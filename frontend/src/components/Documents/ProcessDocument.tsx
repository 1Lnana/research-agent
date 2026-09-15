import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Play } from "lucide-react"

import { type DocumentPublic, DocumentsService } from "@/client"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface ProcessDocumentProps {
  document: DocumentPublic
}

const ProcessDocument = ({ document }: ProcessDocumentProps) => {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const isTextDocument = ["text/plain", "text/markdown"].includes(
    document.file_type,
  )

  const mutation = useMutation({
    mutationFn: () =>
      DocumentsService.processDocument({
        path: { id: document.id },
      }),
    onSuccess: () => {
      showSuccessToast("Document processed successfully")
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] })
    },
  })

  if (document.status === "ready") {
    return <span className="text-sm text-green-600">Ready</span>
  }

  if (!isTextDocument) {
    return (
      <span className="text-sm text-muted-foreground">
        PDF processing coming soon
      </span>
    )
  }

  return (
    <Button
      className="gap-2"
      disabled={mutation.isPending}
      onClick={() => mutation.mutate()}
    >
      <Play className="size-4" />
      {mutation.isPending ? "Processing..." : "Process"}
    </Button>
  )
}

export default ProcessDocument