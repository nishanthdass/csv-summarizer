  

export type TenstackTableProps = {
    zoomLevel: number;
  };

export interface Task {
  task_id: string;
  name: string;
  type: string;  // "table" or "pdf"
  description: string;
  status: string;
  result?: any;
}

