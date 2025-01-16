import React, { useState, useRef } from 'react';
import { useFileSidePanelOperations } from '../hooks/useFileSidePanelOperations';


const UploadWindow: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [errorMsg, setErrorMsg] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { addFileToDatabase, loadTablesFromDatabase, loadPdfsFromDatabase } = useFileSidePanelOperations();


  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setErrorMsg('');
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

      await addFileToDatabase(file);
      await loadTablesFromDatabase();
      await loadPdfsFromDatabase();
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
          accept=".csv,.pdf"
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
