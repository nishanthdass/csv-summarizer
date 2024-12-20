import { useState, useEffect, useCallback } from 'react';

export const useFetchTables = () => {

  const fetchTables = useCallback(async () => {
    try {
      const response = await fetch('http://localhost:8000/get-tables');
      if (response.ok) {
        const data = await response.json();
        return data;
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

  return { fetchTables };
};
