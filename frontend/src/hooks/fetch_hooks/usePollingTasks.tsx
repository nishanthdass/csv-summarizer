import { useRef, useEffect, useState } from "react";
import { Task } from "../../utilities/types";

export const usePollingTasks = (tasks: Task[], setTasks: React.Dispatch<React.SetStateAction<Task[]>>) => {
  const pollingRef = useRef<Set<string>>(new Set());
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const pollTaskStatus = async (taskId: string, tableName: string) => {
    try {
      const response = await fetch(`http://localhost:8000/status/${tableName}/${taskId}`);
      const data = await response.json();
      const { status } = data;

      setTasks((prevTasks) =>
        prevTasks.map((task) =>
          task.task_id === taskId ? { ...task, status } : task
        )
      );

      if (status === "Completed" || status === "Failed") {
        console.log(`Task ${taskId} completed with status: ${status}: `, data);
        
        pollingRef.current.delete(taskId); // Stop polling this task
      }
    } catch (error) {
      console.error(`Error polling task ${taskId}:`, error);
    }
  };

  const addTask = (newTask: Task) => {
    setTasks((prev) => [...prev, newTask]);
    pollingRef.current.add(newTask.task_id);
  };

  useEffect(() => {
    intervalRef.current = setInterval(() => {
      pollingRef.current.forEach((taskId) => {
        const task = tasks.find((task) => task.task_id === taskId);
        if (task) pollTaskStatus(task.task_id, task.table_name);
      });
    }, 3000); // Poll every 3 seconds
  
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [tasks]);

  return { addTask };
};
