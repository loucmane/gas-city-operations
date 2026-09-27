"""Native Codex review admission fixtures; never touches the live queue or services."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from test_jobrunner import COMMIT, WRAPPER, Fixture, J
import export_codex_review as E

AGENT = '11111111-1111-7111-8111-111111111111'
OTHER = '22222222-2222-7222-8222-222222222222'
PARENT = '33333333-3333-7333-8333-333333333333'
TURN = '44444444-4444-7444-8444-444444444444'


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def bundle(agent=AGENT, verdict='SOURCE_PASS', request=None):
    request = request or 'candidate=%s\nWrapper: %s\nRead this frozen request and attest its SHA-256.\n' % (COMMIT, WRAPPER)
    report = '%s %s\nReview-Request-SHA256: %s\nmust_fix: none' % (verdict, COMMIT, sha(request))
    path = '/root/reviewer_' + agent[:8]
    payloads = [
        ('session_meta', {'id': agent, 'parent_thread_id': PARENT, 'thread_source': 'subagent',
                          'model_provider': 'openai', 'source': {'subagent': {'thread_spawn': {
                              'parent_thread_id': PARENT, 'depth': 1, 'agent_path': path}}}}),
        ('event_msg', {'type': 'task_started', 'turn_id': TURN}),
        ('turn_context', {'turn_id': TURN, 'model': 'gpt-6-astra', 'effort': 'high'}),
        ('response_item', {'type': 'agent_message', 'author': '/root', 'recipient': path,
                           'content': [{'type': 'input_text', 'text':
                                        'Message Type: NEW_TASK\nTask name: %s\nSender: /root\nPayload:\n' % path},
                                       {'type': 'encrypted_content', 'encrypted_content': 'synthetic-ciphertext'}]}),
        ('response_item', {'type': 'message', 'role': 'assistant', 'phase': 'final_answer',
                           'content': [{'type': 'output_text', 'text': report}],
                           'internal_chat_message_metadata_passthrough': {'turn_id': TURN}}),
        ('event_msg', {'type': 'task_complete', 'turn_id': TURN, 'last_agent_message': report}),
    ]
    records = [{'ordinal': i, 'type': kind, 'payload': data} for i, (kind, data) in enumerate(payloads)]
    return pack(request, records)


def pack(request, records):
    raw = ''.join(json.dumps(record, sort_keys=True) + '\n' for record in records)
    return {'schema': 'gc.codex-review.v1', 'request': request, 'request_sha256': sha(request),
            'rollout': raw, 'rollout_sha256': sha(raw)}


class CodexReviews(Fixture):
    def file_codex(self, value=None, agent=AGENT):
        value = bundle(agent) if value is None else value
        path = os.path.join(self.review_dir, 'codex-%s.json' % agent)
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump(value, handle)
        return path

    def test_native_codex_and_mixed_provider_pairs_are_admitted(self):
        self.reviews = [self.file_codex(), self.reviews[1]]
        self.assertEqual(J.admit(self.cfg, self.job(), self.deps)['job_id'], 'canary-r2')
        self.reviews = [self.file_codex(), self.file_codex(agent=OTHER)]
        self.assertEqual(J.admit(self.cfg, self.job(), self.deps)['job_id'], 'canary-r2')

    def test_native_hold_is_parsed_but_refuses_the_commit_even_when_not_cited(self):
        path = self.file_codex(bundle(verdict='HOLD'))
        self.assertEqual(J.read_review(path, COMMIT, os.getuid())[2], 'HOLD ' + COMMIT)
        self.refused(self.job(), 'does not pass the commit')

    def test_same_codex_reviewer_twice_is_not_independent(self):
        path = self.file_codex()
        self.refused(self.job(reviews=[path, path]), 'same reviewer')

    def test_wrong_candidate_wrapper_and_request_attestation_refuse(self):
        for change in ('candidate', 'wrapper', 'attestation'):
            with self.subTest(change=change):
                value = bundle()
                if change == 'candidate':
                    value = bundle(request=value['request'].replace(COMMIT, 'b' * 40))
                elif change == 'wrapper':
                    value = bundle(request=value['request'].replace(WRAPPER, 'elsewhere'))
                else:
                    value['request'] += 'Changed after the review.\n'
                    value['request_sha256'] = sha(value['request'])
                path = self.file_codex(value)
                self.refused(self.job(reviews=[path, self.reviews[1]]), '')

    def test_byte_digest_and_envelope_shape_refuse(self):
        for field in ('request_sha256', 'rollout_sha256', 'schema', 'extra'):
            with self.subTest(field=field):
                value = bundle()
                value[field] = 'wrong'
                with self.assertRaises(J.Refuse):
                    J.read_review(self.file_codex(value), COMMIT, os.getuid())

    def test_native_identity_turn_and_completion_guards(self):
        changes = {
            'root_not_subagent': lambda r: r[0]['payload'].update(source='cli'),
            'guardian_not_reviewer': lambda r: r[0]['payload'].update(source={'subagent': {'other': 'guardian'}}),
            'parent_is_self': lambda r: r[0]['payload'].update(parent_thread_id=AGENT),
            'model_mismatch': lambda r: r[2]['payload'].update(model='unreviewed-model'),
            'wrong_turn': lambda r: r[2]['payload'].update(turn_id=OTHER),
            'wrong_recipient': lambda r: r[3]['payload'].update(recipient='/root/somebody_else'),
            'wrong_sender': lambda r: r[3]['payload'].update(author='/root/somebody_else'),
            'missing_final': lambda r: r[4]['payload'].update(phase='commentary'),
            'missing_complete': lambda r: r.pop(),
            'wrong_terminal_text': lambda r: r[-1]['payload'].update(last_agent_message='not the verdict'),
            'aborted': lambda r: r[-1]['payload'].update(type='turn_aborted'),
            'mixed_thread': lambda r: r[-1]['payload'].update(thread_id=OTHER),
            'missing_record': lambda r: r.pop(3),
            'multiple_sessions': lambda r: r.append(copy.deepcopy(r[0])),
            'multiple_tasks': lambda r: r.append(copy.deepcopy(r[1])),
            'trailing_record': lambda r: r.append({'ordinal': len(r), 'type': 'event_msg', 'payload': {}}),
        }
        for label, edit in changes.items():
            with self.subTest(label=label):
                value = bundle()
                rows = [json.loads(x) for x in value['rollout'].splitlines()]
                edit(rows)
                with self.assertRaises(J.Refuse):
                    J.read_review(self.file_codex(pack(value['request'], rows)), COMMIT, os.getuid())

    def test_filename_links_duplicate_keys_and_non_object_payload_refuse(self):
        path = self.file_codex()
        other = os.path.join(self.review_dir, 'codex-%s.json' % OTHER)
        os.rename(path, other)
        with self.assertRaises(J.Refuse):
            J.read_review(other, COMMIT, os.getuid())
        os.symlink(other, path)
        with self.assertRaises(J.Refuse):
            J.read_review(path, COMMIT, os.getuid())
        os.unlink(path)
        value = bundle()
        rows = [json.loads(x) for x in value['rollout'].splitlines()]
        rows[2]['payload'] = None
        with self.assertRaises(J.Refuse):
            J.read_review(self.file_codex(pack(value['request'], rows)), COMMIT, os.getuid())
        raw = json.dumps(bundle()).replace('"schema":', '"schema": "duplicate", "schema":', 1)
        with open(path, 'w') as handle:
            handle.write(raw)
        with self.assertRaises(J.Refuse):
            J.read_review(path, COMMIT, os.getuid())

    def test_complete_numbering_cannot_hide_a_second_turn_or_task(self):
        for index in (0, 1, 2, 3, 4, 5):
            with self.subTest(index=index):
                value = bundle()
                rows = [json.loads(x) for x in value['rollout'].splitlines()]
                rows.insert(index + 1, copy.deepcopy(rows[index]))
                for i, row in enumerate(rows):
                    row['ordinal'] = i
                with self.assertRaises(J.Refuse):
                    J.read_review(self.file_codex(pack(value['request'], rows)), COMMIT, os.getuid())

    def test_tool_output_or_commentary_cannot_supply_a_verdict(self):
        for phase in ('commentary', 'tool_output'):
            value = bundle()
            rows = [json.loads(x) for x in value['rollout'].splitlines()]
            rows[4]['payload']['phase'] = phase
            with self.assertRaises(J.Refuse):
                J.read_review(self.file_codex(pack(value['request'], rows)), COMMIT, os.getuid())

    def test_native_launch_context_is_not_a_second_request(self):
        for index, body, allowed in ((2, '# AGENTS.md instructions for /fixture', True),
                                     (2, '<environment_context>fixture</environment_context>', True),
                                     (2, 'Review something different instead', False),
                                     (4, '<environment_context>fixture</environment_context>', False)):
            with self.subTest(index=index, body=body):
                value = bundle()
                rows = [json.loads(x) for x in value['rollout'].splitlines()]
                rows.insert(index, {'type': 'response_item', 'payload': {
                    'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': body}]}})
                for i, row in enumerate(rows):
                    row['ordinal'] = i
                path = self.file_codex(pack(value['request'], rows))
                if allowed:
                    self.assertEqual(J.read_review(path, COMMIT, os.getuid())[0], 'codex:' + AGENT)
                else:
                    with self.assertRaises(J.Refuse):
                        J.read_review(path, COMMIT, os.getuid())

    def test_unicode_separator_is_text_not_a_native_record_boundary(self):
        value = bundle()
        rows = [json.loads(x) for x in value['rollout'].split('\n') if x]
        rows[4]['payload']['content'][0]['text'] += '\nReview prose\u2028continues here'
        rows[-1]['payload']['last_agent_message'] = rows[4]['payload']['content'][0]['text']
        raw = ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows)
        value.update(rollout=raw, rollout_sha256=sha(raw))
        self.assertEqual(J.read_review(self.file_codex(value), COMMIT, os.getuid())[2], 'SOURCE_PASS ' + COMMIT)

    def test_native_new_task_header_and_encrypted_structure_are_mandatory(self):
        for change in ('null', 'empty_object', 'message', 'wrong_name', 'wrong_sender',
                       'missing_cipher', 'empty_cipher', 'non_string_cipher', 'extra_item', 'reversed'):
            with self.subTest(change=change):
                value = bundle()
                rows = [json.loads(x) for x in value['rollout'].split('\n') if x]
                task = rows[3]['payload']
                content = task['content']
                if change == 'null':
                    task['content'] = [None]
                elif change == 'empty_object':
                    task['content'] = [{}]
                elif change == 'message':
                    content[0]['text'] = content[0]['text'].replace('NEW_TASK', 'MESSAGE')
                elif change == 'wrong_name':
                    content[0]['text'] = content[0]['text'].replace(task['recipient'], '/root/unrelated')
                elif change == 'wrong_sender':
                    content[0]['text'] = content[0]['text'].replace('Sender: /root', 'Sender: /other')
                elif change == 'missing_cipher':
                    content.pop()
                elif change == 'empty_cipher':
                    content[1]['encrypted_content'] = ''
                elif change == 'non_string_cipher':
                    content[1]['encrypted_content'] = {'arbitrary': 'object'}
                elif change == 'extra_item':
                    content.append({'type': 'input_text', 'text': 'another request'})
                else:
                    content.reverse()
                with self.assertRaises(J.Refuse):
                    J.read_review(self.file_codex(pack(value['request'], rows)), COMMIT, os.getuid())

    def test_unsupported_effort_duplicate_attestation_and_invalid_unicode_refuse(self):
        for change in ('effort', 'attestation', 'unicode'):
            value = bundle()
            rows = [json.loads(x) for x in value['rollout'].splitlines()]
            if change == 'effort':
                rows[2]['payload']['effort'] = 'invented'
            elif change == 'attestation':
                rows[4]['payload']['content'][0]['text'] += '\nReview-Request-SHA256: ' + value['request_sha256']
                rows[-1]['payload']['last_agent_message'] = rows[4]['payload']['content'][0]['text']
            else:
                value['request'] += '\ud800'
            if change != 'unicode':
                value = pack(value['request'], rows)
            with self.assertRaises(J.Refuse):
                J.read_review(self.file_codex(value), COMMIT, os.getuid())


class Export(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.request = self.root / 'request.md'
        self.rollout = self.root / ('rollout-2026-09-27T19-00-00-%s.jsonl' % AGENT)
        self.output = self.root / 'exports'
        self.output.mkdir()
        self.value = bundle()
        self.request.write_bytes(self.value['request'].encode('utf-8'))
        self.rollout.write_bytes(self.value['rollout'].encode('utf-8'))

    def run_export(self):
        return E.export(str(self.request), str(self.rollout), str(self.output), COMMIT)

    def test_lossless_create_only_export_does_not_file_or_queue(self):
        before = (self.request.read_bytes(), self.rollout.read_bytes())
        path = self.run_export()
        value = json.loads(Path(path).read_bytes())
        self.assertEqual(value, self.value)
        self.assertEqual(J.read_review(path, COMMIT, os.getuid())[0], 'codex:' + AGENT)
        with self.assertRaises(E.J.Refuse):
            self.run_export()
        self.assertEqual(before, (self.request.read_bytes(), self.rollout.read_bytes()))
        self.assertEqual({x.name for x in self.output.iterdir()}, {'codex-%s.json' % AGENT})

    def test_invalid_provenance_creates_nothing(self):
        self.request.write_text(self.value['request'] + 'changed')
        with self.assertRaises(E.J.Refuse):
            self.run_export()
        self.assertEqual(list(self.output.iterdir()), [])

    def test_input_link_and_output_link_refuse_without_mutation(self):
        target = self.root / 'request-original.md'
        self.request.rename(target)
        self.request.symlink_to(target)
        with self.assertRaises(E.J.Refuse):
            self.run_export()
        self.request.unlink()
        target.rename(self.request)
        self.output.rename(self.root / 'real-exports')
        self.output.symlink_to(self.root / 'real-exports')
        with self.assertRaises(OSError):
            self.run_export()
        self.assertEqual(list(self.output.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
