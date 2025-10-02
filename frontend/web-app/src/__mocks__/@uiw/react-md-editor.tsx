import React from 'react';

interface MDEditorProps {
  value?: string;
  onChange?: (value?: string) => void;
  height?: number;
  preview?: string;
  className?: string;
  textareaProps?: any;
}

const MDEditor: React.FC<MDEditorProps> = ({ value, onChange, textareaProps }) => {
  return (
    <textarea
      data-testid="md-editor"
      value={value}
      onChange={(e) => onChange?.(e.target.value)}
      placeholder={textareaProps?.placeholder}
      className="md-editor-mock"
    />
  );
};

export default MDEditor;
