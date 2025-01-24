import React, { createContext, useContext, useState, useEffect } from "react";
import { Task } from '../utilities/types';

interface TaskContextType {
  tasks: Task[];
  addTask: (newTask: Task) => void;
  removeTask: (taskId: string) => void;
  pollingState: Record<string, boolean>;
}

const TaskContext = createContext<TaskContextType | undefined>(undefined);

export const TaskProvider = ({ children }: { children: React.ReactNode }) => {
  const [tasks, setTasks] = useState<Task[]>([]);

  const addTask = (newTask: Task) => {
    setTasks((prevTasks) => [...prevTasks, newTask]);
  };

  const removeTask = (taskId: string) => {
    setTasks((prevTasks) => prevTasks.filter((task) => task.task_id !== taskId));
  }

  useEffect(() => {
    const interval = setInterval(() => {
      setTasks((prevTasks) =>
        prevTasks.map((task) => {
          if (task.status !== "Completed" && task.status !== "Failed") {
            // Poll task status
            fetch(`http://localhost:8000/status/${task.name}/${task.task_id}`)
              .then((response) => response.json())
              .then((data) => {
                task.status = data.status;
              })
              .catch((error) => {
                console.error(`Error polling task ${task.task_id}:`, error);
              });
          } else if (task.status === "Completed" || task.status === "Failed") {
            console.log(`Task ${task.task_id} completed with status: ${task.status}: `, task);
            removeTask(task.task_id);
          }
          return task;
        })
      );
    }, 3000); // Poll every 3 seconds

    return () => clearInterval(interval);
  }, []);

  const pollingState = tasks.reduce((acc, task) => {
    acc[task.name] = task.status !== "Completed";
    return acc;
  }, {} as Record<string, boolean>);

  return (
    <TaskContext.Provider value={{ tasks, addTask, removeTask, pollingState }}>
      {children}
    </TaskContext.Provider>
  );
};

export const useTasks = () => {
  const context = useContext(TaskContext);
  if (!context) {
    throw new Error('useTasks must be used within a TaskProvider');
  }
  return context;
};
