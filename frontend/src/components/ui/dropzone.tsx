import * as React from "react";
import { motion } from "framer-motion";
import { useDropzone, type DropzoneOptions } from "react-dropzone";
import { cn } from "@/lib/utils";

export interface DropzoneProps
  extends Omit<React.HTMLAttributes<HTMLDivElement>,
    'onDrop' | 'onDrag' | 'onDragStart' | 'onDragEnd' | 'onDragEnter' | 'onDragOver' | 'onDragLeave' | 'onError'>,
    DropzoneOptions {
  onFileUpload?: (files: File[]) => void;
}/**
 * Motion-enabled dropzone that merges react-dropzone props safely.
 * - Uses `any` cast on getRootProps spread to avoid Framer's onDrag typing clash.
 * - ForwardRef so parents can access the div if needed.
 */
const Dropzone = React.forwardRef<HTMLDivElement, DropzoneProps>(function Dropzone({ className, children, onDrop, onFileUpload, ...opts },
  ref
) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    ...(opts as unknown as DropzoneOptions),
    onDrop: (accepted, fileRejections, event) => {
      if (onDrop) (onDrop as any)(accepted, fileRejections, event as any);
      if (onFileUpload) onFileUpload(accepted);
    },
  });

  return (
    <motion.div
      {...(getRootProps() as any)}
      ref={ref}
      className={cn(
        "relative border-2 border-dashed rounded-2xl p-8 text-center transition-all duration-300 ease-in-out",
        "bg-background-panel border-border-subtle",
        isDragActive && "border-accent-cyan-500 bg-accent-cyan-500/10 shadow-md",
        className
      )}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
    >
      {/* Hidden input must be inside the root element */}
      <input {...getInputProps()} />
      {children}
    </motion.div>
  );
});

export default Dropzone;
export { Dropzone };

