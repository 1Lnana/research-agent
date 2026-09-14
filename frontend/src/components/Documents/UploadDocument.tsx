import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Upload } from "lucide-react"
import { useState } from "react"

import { DocumentsService } from "@/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

const UploadDocument = () => {
  const [file, setFile] = useState<File | null>(null)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: (selectedFile: File) =>
      DocumentsService.uploadDocument({
        body: { file: selectedFile },
      }),
    onSuccess: () => {
      showSuccessToast("Document uploaded successfully")
      setFile(null)
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] })
    },
  })

  const handleUpload = () => {
    if (file) {
      mutation.mutate(file)
    }
  }

  return (
    <div className="flex items-center gap-3">
      <Input
        type="file"
        accept=".pdf,.md,.txt"
        onChange={(event) => setFile(event.target.files?.[0] ?? null)}
      />
      <Button
        className="gap-2"
        disabled={!file || mutation.isPending}
        onClick={handleUpload}
      >
        <Upload className="size-4" />
        {mutation.isPending ? "Uploading..." : "Upload"}
      </Button>
    </div>
  )
}

export default UploadDocument