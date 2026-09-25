// Private source-bound observer for the exact native platform integrity API.
package main

import (
 "context"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "fmt"
 "os"
 "time"
 "github.com/gastownhall/gascity/internal/platforminstall"
)

func main() { if err := inspect(); err != nil { fmt.Fprintln(os.Stderr, err); os.Exit(1) } }
func inspect() error {
 if len(os.Args) != 1 { return fmt.Errorf("no caller-selected inputs accepted") }
 const path = "/home/loucmane/gascity/city/.gc/platform/install-manifest.json"
 const want = "2d7eadce62c4e567697813cc9122414f1e94c3bd9d389aef92015adef7f36319"
 info, err := os.Lstat(path); if err != nil { return err }
 if !info.Mode().IsRegular() || info.Mode().Perm() != 0644 { return fmt.Errorf("manifest mode drift") }
 data, err := os.ReadFile(path); if err != nil { return err }
 sum := sha256.Sum256(data)
 if hex.EncodeToString(sum[:]) != want { return fmt.Errorf("manifest bytes drift") }
 manifest, err := platforminstall.LoadManifest(data); if err != nil { return err }
 ctx, cancel := context.WithTimeout(context.Background(), 45*time.Second); defer cancel()
 report, err := platforminstall.InspectIntegrity(ctx, manifest)
 if err != nil { return err }
 if err = json.NewEncoder(os.Stdout).Encode(struct {
  Schema string `json:"schema"`
  OK bool `json:"ok"`
  Report platforminstall.IntegrityReport `json:"report"`
 }{"ga.platform-inspect-observation.v1", len(report.Drifts)==0, report}); err != nil { return err }
 if len(report.Drifts) != 0 { return fmt.Errorf("platform integrity drift") }
 return nil
}
