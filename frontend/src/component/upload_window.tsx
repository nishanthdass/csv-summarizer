import React, { useState } from 'react';

interface UploadWindowProps {
  onSuccessfulUpload: () => void;  // Define a callback prop for successful upload
}

const UploadWindow: React.FC<UploadWindowProps> = ({ onSuccessfulUpload }) => {
  const [file, setFile] = useState<File | null>(null);

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
        onSuccessfulUpload();  // Trigger the callback to reload the file list
      } else {
        console.error('Error uploading file');
      }
    } catch (error) {
      console.error('Error:', error);
    }
  };

  return (
    <div className="upload-section">
      <h2>Upload CSV File</h2>
      <div className="upload-section-input">
        <input type="file" accept=".csv" onChange={handleFileUpload} />
        <button className="upload-button" onClick={uploadFile}>Upload</button>
      </div>
    </div>
  );
};

export default UploadWindow;
