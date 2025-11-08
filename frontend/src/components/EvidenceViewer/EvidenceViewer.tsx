import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Loader2, FileText, Link, Lightbulb } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';

interface Document {
  id: string;
  title: string;
  content: string;
  metadata: Record<string, any>;
}

interface Entity {
  id: string;
  label: string;
  type: string;
}

interface Annotation {
  id: string;
  text: string;
  start: number;
  end: number;
  entity_id?: string;
  type: string; // e.g., 'entity', 'highlight', 'comment'
}

const EvidenceViewer: React.FC = () => {
  const { documentId } = useParams<{ documentId: string }>();
  const [document, setDocument] = useState<Document | null>(null);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!documentId) {
      setError("No document ID provided.");
      setLoading(false);
      return;
    }

    const fetchDocumentData = async () => {
      setLoading(true);
      setError(null);
      try {
        // Placeholder for fetching document content from backend
        // Replace with actual API call to /documents/{documentId}
        const fetchedDocument: Document = {
          id: documentId,
          title: `Document ${documentId}`,
          content: `This is the content of document ${documentId}. It contains various legal terms like "contract", "plaintiff", "defendant", and "judgment". This document discusses a case where a "company" was sued by an individual. The outcome was a "settlement".`,
          metadata: { source: "local", date: "2025-11-02" },
        };
        setDocument(fetchedDocument);

        // Placeholder for fetching linked entities from backend
        // Replace with actual API call to /graph/entities?doc_id={documentId} or similar
        const fetchedEntities: Entity[] = [
          { id: "entity-1", label: "contract", type: "LegalTerm" },
          { id: "entity-2", label: "plaintiff", type: "LegalRole" },
          { id: "entity-3", label: "defendant", type: "LegalRole" },
          { id: "entity-4", label: "judgment", type: "LegalOutcome" },
          { id: "entity-5", label: "company", type: "Organization" },
          { id: "entity-6", label: "settlement", type: "LegalOutcome" },
        ];
        setEntities(fetchedEntities);

        // Generate mock annotations based on entities
        const generatedAnnotations: Annotation[] = fetchedEntities.map(entity => {
          const startIndex = fetchedDocument.content.indexOf(entity.label);
          if (startIndex !== -1) {
            return {
              id: `anno-${entity.id}`,
              text: entity.label,
              start: startIndex,
              end: startIndex + entity.label.length,
              entity_id: entity.id,
              type: 'entity',
            };
          }
          return null;
        }).filter(Boolean) as Annotation[];
        setAnnotations(generatedAnnotations);

      } catch (err) {
        console.error("Failed to fetch document data:", err);
        setError("Failed to load document. Please try again.");
      } finally {
        setLoading(false);
      }
    };

    fetchDocumentData();
  }, [documentId]);

  const renderContentWithAnnotations = () => {
    if (!document) return null;

    const parts: (string | JSX.Element)[] = [];
    let lastIndex = 0;

    // Sort annotations to handle overlapping or nested annotations correctly
    const sortedAnnotations = [...annotations].sort((a, b) => a.start - b.start);

    sortedAnnotations.forEach(annotation => {
      if (annotation.start > lastIndex) {
        parts.push(document.content.substring(lastIndex, annotation.start));
      }
      const entity = entities.find(e => e.id === annotation.entity_id);
      parts.push(
        <span
          key={annotation.id}
          className="relative cursor-pointer bg-blue-200 bg-opacity-30 rounded px-1 py-0.5 hover:bg-blue-300 hover:bg-opacity-50 transition-colors duration-200"
          title={`${entity?.type || annotation.type}: ${annotation.text}`}
        >
          {annotation.text}
          {entity && (
            <Badge variant="secondary" className="ml-1 text-xs bg-blue-500 text-white">
              {entity.type}
            </Badge>
          )}
        </span>
      );
      lastIndex = annotation.end;
    });

    if (lastIndex < document.content.length) {
      parts.push(document.content.substring(lastIndex));
    }

    return <p className="whitespace-pre-wrap text-gray-200 leading-relaxed">{parts}</p>;
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        <span className="ml-2 text-gray-400">Loading document...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex justify-center items-center h-full text-red-500">
        <p>{error}</p>
      </div>
    );
  }

  if (!document) {
    return (
      <div className="flex justify-center items-center h-full text-gray-400">
        <p>Document not found.</p>
      </div>
    );
  }

  return (
    <div className="p-6 bg-gray-900 min-h-screen text-gray-100">
      <Card className="bg-gray-800 border-gray-700 shadow-lg">
        <CardHeader className="border-b border-gray-700">
          <CardTitle className="flex items-center text-blue-400">
            <FileText className="mr-2 h-6 w-6" /> {document.title}
          </CardTitle>
          <p className="text-sm text-gray-400">ID: {document.id}</p>
          <p className="text-xs text-gray-500">Source: {document.metadata.source} | Date: {document.metadata.date}</p>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <h3 className="text-xl font-semibold mb-3 flex items-center"><FileText className="mr-2 h-5 w-5" /> Document Content</h3>
              <ScrollArea className="h-[600px] w-full rounded-md border border-gray-700 p-4 bg-gray-900">
                {renderContentWithAnnotations()}
              </ScrollArea>
            </div>
            <div>
              <h3 className="text-xl font-semibold mb-3 flex items-center"><Link className="mr-2 h-5 w-5" /> Linked Entities</h3>
              <ScrollArea className="h-[290px] w-full rounded-md border border-gray-700 p-4 bg-gray-900 mb-6">
                {entities.length > 0 ? (
                  <div className="space-y-2">
                    {entities.map(entity => (
                      <div key={entity.id} className="flex items-center justify-between p-2 bg-gray-700 rounded-md">
                        <span className="text-gray-100">{entity.label}</span>
                        <Badge variant="outline" className="bg-blue-600 text-white border-blue-600">{entity.type}</Badge>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-400">No entities linked.</p>
                )}
              </ScrollArea>

              <h3 className="text-xl font-semibold mb-3 flex items-center"><Lightbulb className="mr-2 h-5 w-5" /> Annotations</h3>
              <ScrollArea className="h-[290px] w-full rounded-md border border-gray-700 p-4 bg-gray-900">
                {annotations.length > 0 ? (
                  <div className="space-y-2">
                    {annotations.map(anno => (
                      <div key={anno.id} className="p-2 bg-gray-700 rounded-md">
                        <p className="text-gray-100 text-sm">"{anno.text}"</p>
                        <Badge variant="outline" className="mt-1 bg-green-600 text-white border-green-600">{anno.type}</Badge>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-400">No annotations.</p>
                )}
              </ScrollArea>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default EvidenceViewer;
