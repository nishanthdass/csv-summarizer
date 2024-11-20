import { useCallback } from 'react';

export const useDeleteTable = (refresh: () => void) => {
  const deleteTable = useCallback(
    async (tableName: string) => {
      try {
        const response = await fetch('http://localhost:8000/delete-table', {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ table_name: tableName, page: 1, page_size: 10 }),
        });

        if (response.ok) {
          console.log('Table deleted successfully');
          refresh(); // Trigger a refresh on success
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
    [refresh] // Include dependencies here
  );

  return { deleteTable };
};