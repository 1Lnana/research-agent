import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Trash2 } from "lucide-react"

import { type DocumentPublic, DocumentsService } from "@/client"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface DeleteDocumentProps {
  document: DocumentPublic
}

const DeleteDocument = ({ document }: DeleteDocumentProps) => {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()



  const mutation = useMutation({
    mutationFn: () =>
      DocumentsService.deleteDocument({
        path: { id: document.id },
      }),
    onSuccess: () => {
    showSuccessToast("Document deleted successfully")
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] })
    },
  })


  return (
    <Button
      variant="destructive"
      className="gap-2"
      disabled={mutation.isPending}
      onClick={() => {
        if (window.confirm(`Delete ${document.file_name}?`)) {
            mutation.mutate()
          }
        }}
    >
      <Trash2 className="size-4" />
      {mutation.isPending ? "Deleting..." : "Delete"}
    </Button>
  )
}

export default DeleteDocument