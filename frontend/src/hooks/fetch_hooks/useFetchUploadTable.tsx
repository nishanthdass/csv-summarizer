import { useCallback } from 'react';
import { usePollingTasks } from '../../hooks/fetch_hooks/usePollingTasks';
import { useTasks } from '../../context/useTaskContext';
import { useDataContext } from '../../context/useDataContext';

export const useFetchUploadTable = () => {
  const { tasks, setTasks } = useTasks();
  const { addTask } = usePollingTasks(tasks, setTasks);

  const fetchUploadTable = useCallback(
    async (file: File): Promise<void> => {
      const formData = new FormData();
      formData.append('file', file);

      try {
        const response = await fetch('http://localhost:8000/upload', {
          method: 'POST',
          body: formData,
        });

        if (response.ok) {
          const data = await response.json();

          // Add task
          addTask({
            task_id: data.task.task_id,
            table_name: data.task.table_name,
            description: data.task.description,
            status: data.task.status,
            result: data.task.result,
          });

        } else {
          throw new Error('Error uploading file');
        }
      } catch (error) {
        console.error('Error during upload:', error);
        throw error; // Allow the component to handle errors
      }
    },
    [addTask]
  );

  return { fetchUploadTable };
};
