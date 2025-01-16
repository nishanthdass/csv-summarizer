import { useCallback } from 'react';

export const useFetchUploadDeleteFile = () => {
  
  const fetchUploadFile = useCallback(
    async (file: File): Promise<any> => {
      const formData = new FormData();
      formData.append('file', file);

      try {
        const response = await fetch('http://localhost:8000/upload', {
          method: 'POST',
          body: formData,
        });

        if (response.ok) {
          return await response.json();
        } else {
          throw new Error('Error uploading file');
        }
      } catch (error) {
        console.error('Error during upload:', error);
        throw error;
      }
    },
    []
  );

  const fetchDeleteFile = useCallback(
    async (tableName: string) => {
      try {
        const response = await fetch('http://localhost:8000/delete-file', {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ table_name: tableName }),
        });

        if (response.ok) {
          console.log('Table deleted successfully');
        } else {
          const error = await response.text();
          console.error('Error deleting table:', error);
          throw new Error(error);
        }
      } catch (error) {
        console.error('Error:', error);
        throw error;
      }
    },
    []
  );

  return { fetchUploadFile, fetchDeleteFile };
};
