// Private diagnostic: configuration composition only; never installed or dispatched.
// P10: the P8 composition for the Operations candidate identity (PATH is its only agent override).
package main

import (
 "encoding/json"
 "fmt"
 "os"
 "os/exec"
 "path/filepath"
 "strings"

 "github.com/gastownhall/gascity/internal/config"
 "github.com/gastownhall/gascity/internal/convergence"
 "github.com/gastownhall/gascity/internal/fsys"
 "github.com/gastownhall/gascity/internal/processenv"
 "github.com/gastownhall/gascity/internal/shellquote"
)

const city = "/home/loucmane/gascity/city"
const target = "gascity/operations-candidate-worker"

type observation struct {
 Schema string `json:"schema"`
 Profile string `json:"profile"`
 Argv []string `json:"argv"`
 Environment map[string]string `json:"environment"`
 Revision string `json:"permission_revision"`
 TaskObserved bool `json:"task_observed"`
 WorkerLaunched bool `json:"worker_launched"`
}

func main() {
 if err := run(); err != nil { fmt.Fprintln(os.Stderr, err); os.Exit(1) }
}

func run() error {
 if len(os.Args) != 1 { return fmt.Errorf("composition diagnostic accepts no arguments") }
 cfg, prov, err := config.LoadWithIncludes(fsys.OSFS{}, filepath.Join(city, "city.toml"))
 if err != nil { return err }
 a := config.FindAgent(cfg, target)
 if a == nil || a.QualifiedName() != target || a.Upstream != "" {
  return fmt.Errorf("agent/upstream mismatch")
 }
 p, err := config.ResolveProvider(a, &cfg.Workspace, cfg.Providers, exec.LookPath)
 if err != nil { return err }
 if p.BuiltinAncestor != "claude" || p.Name != "claude-candidate" {
  return fmt.Errorf("provider mismatch")
 }
 for _, key := range []string{"PATH"} {
  if a.Env[key] == "" || strings.Contains(a.Env[key], "$") {
   return fmt.Errorf("nonliteral agent override %s", key)
  }
 }
 // Genuine supervisor identity is verified outside the mount namespace.
 // This fixed path substitutes only for os.Executable(), which would name
 // the diagnostic here. It is not itself an observation of the supervisor.
 gcBin := "/home/loucmane/gascity/bin/gc"
 env := mergeEnv(passthroughEnv(), expandEnvMap(cfg.Workspace.Env), expandEnvMap(p.Env), expandEnvMap(a.Env), map[string]string{"GC_BIN":gcBin})
 processenv.PrependGCBinDirToPATH(env, env["GC_BIN"])
 env = convergence.ScrubTokenEnv(env)
 declared := map[string]string{}
 for _, key := range []string{"PATH"} { declared[key] = env[key] }
 launch, err := config.BuildProviderLaunchCommand(city, p, nil, "")
 if err != nil { return err }
 // Same cfg/provenance instance for resolution and revision; no second load.
 out := observation{Schema:"gct.configuration-composition-observation.v1", Profile:target,
  Argv:shellquote.Split(launch.Command), Environment:declared,
  Revision:config.Revision(fsys.OSFS{}, prov, cfg, city)}
 return json.NewEncoder(os.Stdout).Encode(out)
}
