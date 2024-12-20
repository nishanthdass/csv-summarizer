import { useCallback } from 'react';

export const useFetchUploadTable = () => {
  const fetchUploadTable = useCallback(
    async (file: File): Promise<any> => {
      const formData = new FormData();
      formData.append('file', file);

      try {
        const response = await fetch('http://localhost:8000/upload', {
          method: 'POST',
          body: formData,
        });

        if (response.ok) {
          return await response.json(); // Return the parsed response data
        } else {
          throw new Error('Error uploading file');
        }
      } catch (error) {
        console.error('Error during upload:', error);
        throw error; // Allow the component to handle errors
      }
    },
    []
  );

  return { fetchUploadTable };
};
