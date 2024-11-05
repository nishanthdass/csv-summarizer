import React, { useState, useRef } from 'react';
import { useFetchTables } from '../hooks/fetch_hooks/useFetchTables';

interface UploadWindowProps {
  onSuccessfulUpload: () => void;
}

const UploadWindow: React.FC<UploadWindowProps> = ({ onSuccessfulUpload }) => {
  const [file, setFile] = useState<File | null>(null);
  const [errorMsg, setErrMsg] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null); // Create a ref for the input element
  const tables = useFetchTables();

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
    }
  };

  const uploadFile = async () => {
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        console.log('File uploaded successfully');
        onSuccessfulUpload();
        setFile(null);
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      } else {
        console.error('Error uploading file');
        setErrMsg('Error uploading file');
      }
    } catch (error) {
      console.error('Error:', error);
      setErrMsg('Error uploading file');
    }
  };

  return (
    <div>
      <div className="upload-section-input">
        <input
          type="file"
          accept=".csv"
          onChange={handleFileUpload}
          ref={fileInputRef} // Attach the ref to the input element
        />
        <button className="upload-button" onClick={uploadFile}>Upload</button>
      </div>
      {errorMsg && <p className="error-message" style={{ color: 'red' }}>{errorMsg}</p>}
    </div>
  );
};

export default UploadWindow;
