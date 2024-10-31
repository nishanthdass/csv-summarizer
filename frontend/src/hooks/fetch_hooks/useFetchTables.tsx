import { useState, useEffect, useCallback } from 'react';

export const useFetchTables = () => {
  const [tables, setTables] = useState<string[]>([]);

  const fetchTables = useCallback(async () => {
    try {
      const response = await fetch('http://localhost:8000/get-tables');
      if (response.ok) {
        const data = await response.json();
        setTables(data);
      } else {
        console.error('Error fetching tables');
      }
    } catch (error) {
      console.error('Error:', error);
    }
  }, []);

  useEffect(() => {
    fetchTables();
  }, [fetchTables]);

  return { tables, refresh: fetchTables };
};
