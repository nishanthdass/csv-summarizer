import { useCallback } from 'react';

export const useDeleteTable = () => {
  const deleteTable = useCallback(
    async (tableName: string) => {
      try {
        const response = await fetch('http://localhost:8000/delete-table', {
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

  return { deleteTable };
};