package managedworker_test

import (
	"context"
	"os"
	"testing"

	"github.com/gastownhall/gascity/internal/api"
	"github.com/gastownhall/gascity/internal/fsys"
	"github.com/gastownhall/gascity/internal/managedworker"
	"github.com/gastownhall/gascity/internal/platforminstall"
)

// TestTemplateManagedWorkerInterop exercises the exact pinned-Core decoder,
// safe policy reader and launch Preflight for the Template candidate profile.
// It stays in an external package so importing internal/api cannot create the
// managedworker -> api -> managedworker test cycle an internal overlay would.
func TestTemplateManagedWorkerInterop(t *testing.T) {
	receiptPath := os.Getenv("GCT_TEMPLATE_RECEIPT")
	profileName := os.Getenv("GCT_TEMPLATE_PROFILE")
	unsafePolicy := os.Getenv("GCT_TEMPLATE_UNSAFE_POLICY")
	if receiptPath == "" || profileName == "" || unsafePolicy == "" {
		t.Fatal("Template candidate interoperability inputs are required")
	}
	receiptBytes, err := os.ReadFile(receiptPath)
	if err != nil {
		t.Fatal(err)
	}
	receipt, err := managedworker.LoadProvisioningReceipt(receiptBytes)
	if err != nil {
		t.Fatalf("load Template candidate receipt: %v", err)
	}
	profile, ok := receipt.Profile(profileName)
	if !ok {
		t.Fatalf("Template candidate profile %q is absent", profileName)
	}
	if profile.EffectiveProfileKind() != managedworker.ProfileKindCandidate {
		t.Fatalf("profile kind = %q, want candidate", profile.EffectiveProfileKind())
	}
	if profile.Provider.Name != "claude" {
		t.Fatalf("provider name = %q, want claude", profile.Provider.Name)
	}

	readPolicy := func(path string) ([]byte, error) {
		return managedworker.ReadControlPolicy(fsys.OSFS{}, path)
	}
	if _, err := readPolicy(profile.ControlPolicy.Path); err != nil {
		t.Fatalf("safe Template policy refused: %v", err)
	}
	if _, err := managedworker.ReadControlPolicy(fsys.OSFS{}, unsafePolicy); err == nil {
		t.Fatal("group-writable Template policy was accepted")
	}

	report, err := managedworker.Preflight(
		context.Background(),
		managedworker.PreflightRequest{
			CheckPath:          profile.CheckPath.Path,
			ObservedProfile:    profile,
			PermissionRevision: receipt.PermissionRevision,
			ProfileName:        profile.Name,
			Receipt:            receiptBytes,
		},
		managedworker.Probes{
			ReadFile:          os.ReadFile,
			ReadControlPolicy: readPolicy,
			InspectProvider:   platforminstall.VerifyProviderPin,
			InspectToolchain: func(_ context.Context, pin managedworker.ToolchainPin, _ map[string]string) error {
				if pin.Name != "python" {
					t.Fatalf("unexpected toolchain %q", pin.Name)
				}
				return nil
			},
			ProbeReadiness: func(_ context.Context, name string) error {
				if name != "claude" || !api.SupportsProviderReadiness(name) {
					t.Fatalf("Core does not support readiness for %q", name)
				}
				return nil
			},
		},
	)
	if err != nil {
		t.Fatalf("Template candidate Preflight: %v", err)
	}
	if !report.OK {
		t.Fatalf("Template candidate Preflight report is not OK: %#v", report)
	}
}
