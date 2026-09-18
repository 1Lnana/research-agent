import { useQuery } from "@tanstack/react-query"
import { useState } from "react"

import { type DocumentPublic, DocumentsService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

type ViewDocumentChunksProps = {
  document: DocumentPublic
}

const ViewDocumentChunks = ({ document }: ViewDocumentChunksProps) => {
  const [isOpen, setIsOpen] = useState(false)

  const { data: chunks = [], isLoading } = useQuery({
    queryKey: ["document-chunks", document.id],
    queryFn: async () =>
      (
        await DocumentsService.readDocumentChunks({
          path: { id: document.id },
        })
      ).data,
    enabled: isOpen,
  })

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" disabled={document.status !== "ready"}>
          View chunks
        </Button>
      </DialogTrigger>

      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{document.file_name}</DialogTitle>
          <DialogDescription>
            Text pieces saved after processing this document.
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <p>Loading chunks...</p>
        ) : chunks.length === 0 ? (
          <p>No chunks found.</p>
        ) : (
          <div className="max-h-96 space-y-3 overflow-y-auto">
            {chunks.map((chunk) => (
              <div key={chunk.id} className="rounded-md border p-3">
                <p className="mb-1 text-sm font-medium">
                  Chunk {chunk.chunk_index + 1}
                </p>
                <p className="whitespace-pre-wrap text-sm">{chunk.content}</p>
              </div>
            ))}
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

export default ViewDocumentChunks