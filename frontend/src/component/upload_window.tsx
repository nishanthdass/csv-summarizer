import React, { useState, useRef } from 'react';
import { useFetchUploadTable } from '../hooks/fetch_hooks/useFetchUploadTable';
import { useDataContext } from '../context/useDataContext';

const UploadWindow: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [errorMsg, setErrorMsg] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { addTable, refresh } = useDataContext();


  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setErrorMsg(''); // Clear previous errors
    }
  };

  const resetFileInput = () => {
    setFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    try {
      await addTable(file);
      refresh();
      resetFileInput();
    } catch (error) {
      setErrorMsg('Error uploading file');
    }
  };

  return (
    <div>
      <div className="upload-section-input">
        <input
          type="file"
          accept=".csv"
          onChange={handleFileUpload}
          ref={fileInputRef}
        />
        <button className="upload-button" onClick={handleUpload}>
          Upload
        </button>
      </div>
      {errorMsg && <p className="error-message" style={{ color: 'red' }}>{errorMsg}</p>}
    </div>
  );
};

export default UploadWindow;
