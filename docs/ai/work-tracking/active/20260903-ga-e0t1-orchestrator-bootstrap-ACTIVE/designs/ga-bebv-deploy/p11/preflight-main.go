// Private receipt preparation: actual native probes, no routed-task assertion.
// P10: the P8 preflight for the one profile the composition names, in a receipt of one or more
// profiles. The environment key set is that profile's own, not the signing profile's three keys.
package main

import (
 "context"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "os"
 "os/exec"
 "path/filepath"
 "reflect"
 "runtime"
 "strings"
 "time"

 "github.com/gastownhall/gascity/internal/api"
 "github.com/gastownhall/gascity/internal/fsys"
 "github.com/gastownhall/gascity/internal/managedworker"
 "github.com/gastownhall/gascity/internal/platforminstall"
 "github.com/gastownhall/gascity/internal/searchpath"
)

var managedWorkerSignerFrontend = "/usr/local/libexec/gas-city/managed-git-commit"
var providerProbeGOOS = runtime.GOOS
var providerProbePathEnv = "/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin"
var providerProbeExpandDirs = searchpath.Expand

type composed struct {
 Observation struct {
  Schema string `json:"schema"`
  Profile string `json:"profile"`
  Argv []string `json:"argv"`
  Environment map[string]string `json:"environment"`
  Revision string `json:"permission_revision"`
  TaskObserved bool `json:"task_observed"`
  WorkerLaunched bool `json:"worker_launched"`
 } `json:"observation"`
}

func nativeIdentity() (string,string,string,error) {
 path, ok := findProbeBinary("claude", "/home/loucmane")
 if !ok { return "","","",fmt.Errorf("native Claude absent from real API discovery path") }
 resolved, err := filepath.EvalSymlinks(path); if err != nil { return "","","",err }
 raw, err := os.ReadFile(resolved); if err != nil { return "","","",err }
 digest := sha256.Sum256(raw)
 return path,resolved,hex.EncodeToString(digest[:]),nil
}

func main(){if err:=run();err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}}
func run() error {
 if len(os.Args)==2 && os.Args[1]=="discover" {
  path,resolved,digest,err:=nativeIdentity(); if err!=nil{return err}
  return json.NewEncoder(os.Stdout).Encode(map[string]any{"path":path,"resolved_path":resolved,"sha256":digest,"provider_invoked":false})
 }
 if len(os.Args)==3 && os.Args[1]=="finalize" {
  raw,err:=os.ReadFile(os.Args[2]); if err!=nil{return err}
  var receipt managedworker.ProvisioningReceipt
  if err=json.Unmarshal(raw,&receipt);err!=nil{return err}
  receipt.ReceiptSHA256=""
  for i:=range receipt.Profiles{receipt.Profiles[i].WorkerProfileSHA256=""}
  _,wire,err:=managedworker.FinalizeProvisioningReceipt(receipt);if err!=nil{return err}
  _,err=os.Stdout.Write(wire);return err
 }
 if len(os.Args)!=5 || (os.Args[1]!="preflight" && os.Args[1]!="negative-old-path") {
  return fmt.Errorf("require discover, finalize INPUT, or preflight/negative-old-path RECEIPT COMPOSITION NATIVE_SHA")
 }
 mode:=os.Args[1]
 wire,err:=os.ReadFile(os.Args[2]);if err!=nil{return err}
 receipt,err:=managedworker.LoadProvisioningReceipt(wire);if err!=nil{return err}
 if len(receipt.Profiles)<1{return fmt.Errorf("at least one profile required")}
 raw,err:=os.ReadFile(os.Args[3]);if err!=nil{return err}
 var evidence composed
 if err=json.Unmarshal(raw,&evidence);err!=nil{return err}
 obs:=evidence.Observation
 expected,ok:=receipt.Profile(obs.Profile)
 if !ok || obs.Schema!="gct.configuration-composition-observation.v1" || obs.TaskObserved || obs.WorkerLaunched {
  return fmt.Errorf("composition binding mismatch")
 }
 if len(expected.Environment)==0 || len(obs.Environment)!=len(expected.Environment){return fmt.Errorf("environment key set changed")}
 for key:=range expected.Environment{if obs.Environment[key]==""{return fmt.Errorf("missing composition environment")}}
 observed:=expected
 observed.Argv=append([]string(nil),obs.Argv...)
 observed.Environment=map[string]string{}
 for key,value:=range obs.Environment{observed.Environment[key]=value}
 if mode=="negative-old-path"{
  observed.Environment["PATH"]=obs.Environment["PATH"]+":/nonexistent-negative"
 }
 path,resolved,digest,err:=nativeIdentity();if err!=nil{return err}
 if digest!=os.Args[4]{return fmt.Errorf("API-discovered native Claude digest drift")}
 ctx,cancel:=context.WithTimeout(context.Background(),35*time.Second);defer cancel()
 report,probeErr:=managedworker.Preflight(ctx,managedworker.PreflightRequest{
  Receipt:wire,ProfileName:obs.Profile,ObservedProfile:observed,
  PermissionRevision:obs.Revision,CheckPath:expected.CheckPath.Path,
 },defaultManagedWorkerPreflightProbes())
 result:=map[string]any{"report":report,"check_path_basis":"receipt-input-not-routed-bead",
  "task_claim_proven":false,"controller_launch_proven":false,"worker_launched":false,
  "inference":false,"signing":false,"receipt_installed":false,
  "native_claude_path":path,"native_claude_resolved":resolved,"native_claude_sha256":digest}
 if probeErr!=nil{result["error"]=probeErr.Error()}
 if err=json.NewEncoder(os.Stdout).Encode(result);err!=nil{return err}
 if mode=="negative-old-path"{
  if probeErr==nil || !strings.Contains(probeErr.Error(),"worker_profile_sha256 mismatch") || !reflect.DeepEqual(report.Checks,[]string{"receipt","profile","permission_revision","check_path_stamp"}){
   return fmt.Errorf("negative did not stop at exact profile comparison")
  }
  return nil
 }
 if probeErr!=nil{return probeErr};if !report.OK{return fmt.Errorf("incomplete probes")};return nil
}

// Exact production functions are appended mechanically from verified Core blobs.
