import React, { createContext, useContext, useState, useEffect } from "react";
import { Task } from '../utilities/types'; 
interface TaskContextType {
  tasks: Task[];
  setTasks: React.Dispatch<React.SetStateAction<Task[]>>;
  pollingState: Record<string, boolean>;
}

const TaskContext = createContext<TaskContextType | undefined>(undefined);

export const TaskProvider = ({ children }: { children: React.ReactNode }) => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [pollingState, setPollingState] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const updatePollingState = () => {
      const newPollingState = tasks.reduce((acc, task) => {
        acc[task.table_name] = task.status !== "Completed";
        return acc;
      }, {} as Record<string, boolean>);
      setPollingState(newPollingState);
    };

    updatePollingState();
  }, [tasks]);

  return (
    <TaskContext.Provider value={{ tasks, setTasks, pollingState }}>
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
