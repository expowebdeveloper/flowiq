import { useState, useRef } from "react"
import { 
  UploadCloud, 
  FileText, 
  Settings2, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  Info, 
  Play, 
  Sparkles, 
  Trash2,
  AlertCircle
} from "lucide-react"

import { PageHeader } from "@/components/shared/PageHeader"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { jsonVerifyService } from "@/services/jsonVerifyService"
import type { JsonVerifyResult } from "@/services/jsonVerifyService"


export function JsonVerifyPage() {
  const [activeTab, setActiveTab] = useState<string>("upload")
  const [file, setFile] = useState<File | null>(null)
  const [rawJson, setRawJson] = useState<string>("")
  
  // Options state
  const [verify, setVerify] = useState<boolean>(true)

  // Result state
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false)
  const [result, setResult] = useState<JsonVerifyResult | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0]
    if (selected) {
      setFile(selected)
      setResult(null)
      setErrorMsg(null)
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const selected = e.dataTransfer.files?.[0]
    if (selected && selected.name.endsWith(".json")) {
      setFile(selected)
      setResult(null)
      setErrorMsg(null)
    } else {
      setErrorMsg("Please upload a valid .json file")
    }
  }

  const clearFile = () => {
    setFile(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
    setResult(null)
  }

  const handleVerify = async () => {
    setResult(null)
    setErrorMsg(null)
    setIsSubmitting(true)

    const formData = new FormData()
    formData.append("verify", String(verify))

    if (activeTab === "upload") {
      if (!file) {
        setErrorMsg("Please select a JSON file to upload.")
        setIsSubmitting(false)
        return
      }
      formData.append("file", file)
    } else {
      if (!rawJson.trim()) {
        setErrorMsg("Please paste your raw JSON data.")
        setIsSubmitting(false)
        return
      }
      formData.append("raw_json", rawJson)
    }

    try {
      const response = await jsonVerifyService.verify(formData)
      if (response.ok && response.data) {
        setResult(response.data)
      } else {
        setErrorMsg(response.errorMessage ?? "Verification request failed.")
      }
    } catch (err) {
      setErrorMsg("An unexpected error occurred during verification.")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <PageHeader
        title="JSON Validation Console"
        description="Verify applicant loan JSON payloads against bank schemas and minimum criteria requirements dynamically."
      />

      <div className="grid gap-6 md:grid-cols-3">
        {/* Left / Config Section */}
        <div className="space-y-6 md:col-span-2">
          <Card className="border border-border/60 shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base font-semibold">
                <FileText className="size-4 text-primary" /> Input Payload Data
              </CardTitle>
              <CardDescription>
                Select your validation input method below.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs value={activeTab} onValueChange={(val) => { setActiveTab(val); setResult(null); }} className="w-full">
                <TabsList className="grid w-full grid-cols-2 mb-4">
                  <TabsTrigger value="upload" className="flex items-center gap-1.5">
                    <UploadCloud className="size-4" /> Upload JSON File
                  </TabsTrigger>
                  <TabsTrigger value="paste" className="flex items-center gap-1.5">
                    <FileText className="size-4" /> Paste Raw JSON
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="upload">
                  <div
                    onDragOver={handleDragOver}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                    className="flex flex-col items-center justify-center border-2 border-dashed border-border/80 hover:border-primary/50 transition-all rounded-xl p-8 cursor-pointer text-center bg-muted/20 hover:bg-muted/40 min-h-[220px]"
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".json"
                      onChange={handleFileChange}
                      className="hidden"
                    />
                    
                    {!file ? (
                      <div className="space-y-3">
                        <div className="mx-auto flex size-12 items-center justify-center rounded-full bg-primary/10 text-primary">
                          <UploadCloud className="size-6" />
                        </div>
                        <div>
                          <p className="text-sm font-medium">Drag & drop your JSON file here</p>
                          <p className="text-xs text-muted-foreground mt-1">or click to browse from files</p>
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-4 w-full max-w-md">
                        <div className="flex items-center justify-between p-3 rounded-lg bg-card border border-border shadow-sm">
                          <div className="flex items-center gap-3 overflow-hidden">
                            <div className="p-2 rounded bg-primary/10 text-primary shrink-0">
                              <FileText className="size-5" />
                            </div>
                            <div className="text-left overflow-hidden">
                              <p className="text-xs font-semibold truncate">{file.name}</p>
                              <p className="text-[10px] text-muted-foreground">{(file.size / 1024).toFixed(2)} KB</p>
                            </div>
                          </div>
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="text-muted-foreground hover:text-destructive shrink-0"
                            onClick={(e) => {
                              e.stopPropagation();
                              clearFile();
                            }}
                          >
                            <Trash2 className="size-4" />
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                </TabsContent>

                <TabsContent value="paste">
                  <Textarea
                    placeholder={`{\n  "applicant_name": "Jane Doe",\n  "applicant_phone": "9876543210",\n  "applicant_email": "jane@example.com",\n  "date_of_birth": "1992-05-15",\n  "gender": "Female",\n  "address": "456 Oak Lane, Mumbai",\n  "credit_score": 750,\n  "monthly_income": 45000,\n  "bank_name": "HDFC Bank",\n  "documents": ["Selfie", "Aadhaar Card", "PAN Card", "Latest 3 Months Salary Slips"]\n}`}
                    value={rawJson}
                    onChange={(e) => setRawJson(e.target.value)}
                    rows={10}
                    className="font-mono text-xs leading-relaxed"
                  />
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>

        {/* Right / Options Section */}
        <div className="space-y-6">
          <Card className="border border-border/60 shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base font-semibold">
                <Settings2 className="size-4 text-primary" /> Configuration Options
              </CardTitle>
              <CardDescription>
                Choose whether to run full verification or manually mark as unverified.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-start justify-between gap-4 p-2 rounded-lg hover:bg-muted/30 transition-colors">
                <div className="space-y-0.5">
                  <Label className="text-sm font-semibold">{verify ? "Verified" : "Unverified"}</Label>
                  <p className="text-xs text-muted-foreground leading-normal">
                    {verify
                      ? "Runs full schema, eligibility, and document validation against require.json."
                      : "Bypasses validation and manually stores this payload as unverified."}
                  </p>
                </div>
                <Switch
                  checked={verify}
                  onCheckedChange={setVerify}
                />
              </div>

              <div className="pt-2 border-t border-border/60">
                <Button 
                  onClick={handleVerify}
                  className="w-full flex items-center justify-center gap-2 font-medium"
                  disabled={isSubmitting}
                >
                  <Play className="size-4 fill-current" />
                  {isSubmitting ? "Saving..." : verify ? "Verify JSON Payload" : "Save as Unverified"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Error Banner */}
      {errorMsg && (
        <div className="flex items-start gap-2.5 rounded-lg border border-destructive/20 bg-destructive/10 p-4 text-sm text-destructive shadow-sm">
          <AlertCircle className="size-4 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h4 className="font-semibold leading-none">Error</h4>
            <p className="text-xs text-destructive/90">{errorMsg}</p>
          </div>
        </div>
      )}

      {/* Results Section */}
      {result && (
        <Card className="border border-border/80 shadow-md overflow-hidden">
          <div className={`h-1.5 ${
            result.status === "verified" ? "bg-emerald-500" :
            result.status === "unverified" ? "bg-amber-500" : "bg-destructive"
          }`} />
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-lg font-semibold flex items-center gap-2">
                {result.status === "verified" && <CheckCircle2 className="size-5 text-emerald-500" />}
                {result.status === "unverified" && <Info className="size-5 text-amber-500" />}
                {result.status === "failed" && <XCircle className="size-5 text-destructive" />}
                {result.status === "error" && <AlertTriangle className="size-5 text-destructive" />}
                <span>
                  {result.status === "verified" ? "Verification Passed" :
                   result.status === "unverified" ? "Verification Bypassed" :
                   result.status === "failed" ? "Verification Failed" : "Verification Processing Error"}
                </span>
              </CardTitle>
              <CardDescription className="mt-1">
                {result.message || "Detailed verification analysis reports below."}
              </CardDescription>
            </div>
            <Badge variant={
              result.status === "verified" ? "secondary" : 
              result.status === "unverified" ? "outline" : "destructive"
            } className="text-xs px-2.5 py-0.5">
              {result.status.toUpperCase()}
            </Badge>
          </CardHeader>
          
          <CardContent className="space-y-4">
            {/* Success Banner */}
            {result.status === "verified" && (
              <div className="flex items-start gap-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 p-4 text-xs text-emerald-700 dark:text-emerald-400">
                <Sparkles className="size-4 shrink-0 mt-0.5" />
                <p>The JSON data fully conforms to all mandatory requirements and eligibility guidelines defined in require.json.</p>
              </div>
            )}

            {/* Error Lists */}
            {result.errors.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-semibold flex items-center gap-1.5 text-destructive">
                  <XCircle className="size-4" /> Errors & Violations ({result.errors.length})
                </h4>
                <ul className="rounded-lg border border-destructive/10 bg-destructive/5 p-3 space-y-2">
                  {result.errors.map((err, i) => (
                    <li key={i} className="flex gap-2 text-xs text-destructive/95 align-top">
                      <span className="shrink-0">•</span>
                      <span>{err}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Warning Lists */}
            {result.warnings.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-semibold flex items-center gap-1.5 text-amber-600 dark:text-amber-400">
                  <AlertTriangle className="size-4" /> Optimization Warnings ({result.warnings.length})
                </h4>
                <ul className="rounded-lg border border-amber-500/10 bg-amber-500/5 p-3 space-y-2">
                  {result.warnings.map((warn, i) => (
                    <li key={i} className="flex gap-2 text-xs text-amber-800 dark:text-amber-400 align-top">
                      <span className="shrink-0">•</span>
                      <span>{warn}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
