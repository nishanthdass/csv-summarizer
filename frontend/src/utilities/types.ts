  

export type TenstackTableProps = {
    zoomLevel: number;
  };

export interface Task {
  task_id: string;
  table_name: string;
  description: string;
  status: string;
  result?: any;
}