import DeleteDocument from "@/components/Documents/DeleteDocument"
import UploadDocument from "@/components/Documents/UploadDocument"
import ProcessDocument from "@/components/Documents/ProcessDocument"
import ViewDocumentChunks from "@/components/Documents/ViewDocumentChunks"
import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { FileText } from "lucide-react"
import { Suspense } from "react"


import { DocumentsService } from "@/client"

function getDocumentsQueryOptions() {
  return {
    queryFn: async () =>
      (
        await DocumentsService.readDocuments({
          query: { skip: 0, limit: 100 },
        })
      ).data,
    queryKey: ["documents"],
  }
}

export const Route = createFileRoute("/_layout/documents")({
  component: Documents,
  head: () => ({
    meta: [{ title: "Documents - Research Assistant" }],
  }),
})

function DocumentsListContent() {
  const { data: documents } = useSuspenseQuery(getDocumentsQueryOptions())

  if (documents.data.length === 0) {
    return <p className="text-muted-foreground">No documents uploaded yet.</p>
  }

  return (
    <div className="space-y-3">
      {documents.data.map((document) => (
        <div
          key={document.id}
          className="flex items-center gap-3 rounded-lg border p-4"
        >
          <FileText className="size-5 text-muted-foreground" />
          <div>
            <p className="font-medium">{document.file_name}</p>
            <p className="text-sm text-muted-foreground">
              {document.file_type} · {document.status}
            </p>
          </div>
          <ProcessDocument document={document} />
          <ViewDocumentChunks document={document} />
          <DeleteDocument document={document} />
        </div>
      ))}
    </div>
  )
}

function Documents() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between gap-4">
  <div>
    <h1 className="text-2xl font-bold tracking-tight">My Documents</h1>
    <p className="text-muted-foreground">
      Upload and manage your personal study materials
    </p>
  </div>
  <UploadDocument />
        </div>

      <Suspense fallback={<p>Loading documents...</p>}>
        <DocumentsListContent />
      </Suspense>
    </div>
  )
}