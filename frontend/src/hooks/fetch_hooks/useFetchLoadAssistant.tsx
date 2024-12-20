import { useCallback } from 'react';

export const useFetchLoadAssistant = () => {

  const fetchLoadAssistant = useCallback(async (tableName: string) => {
    try {
      const response = await fetch('http://localhost:8000/load-assistant', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ table_name: tableName }),
      });

      if (!response.ok) {
        throw new Error(`Error fetching table data: ${response.statusText}`);
      }

      const data = await response.json();
      console.log(data);
      return data;
      
    } catch (error) {
      console.error('Error:', error);
      throw new Error('Failed to fetch table data');
    }
  }, []);

  return { fetchLoadAssistant };

};
