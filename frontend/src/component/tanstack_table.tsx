import React, { useMemo, useEffect } from 'react';

import {
  useReactTable,
  ColumnResizeMode,
  createColumnHelper,
  getCoreRowModel,
  flexRender,
  ColumnResizeDirection
} from '@tanstack/react-table';
import { set } from 'lodash';

type TenstackTableProps = {
  tableName: string;
  table: { 
    header: { [key: string]: string }; 
    rows: any[]; 
    page: number; 
    page_size: number; 
    total_rows: number; 
    total_pages: number;
  };
  fetchData: (page: number, pageSize: number) => void;
  zoomLevel: number;
};

type AiContextObject = {
  tableName: string;
  column: string;
  row: number;
  value: any;
};


const columnHelper = createColumnHelper<any>();

const TenstackTable: React.FC<TenstackTableProps> = ({ tableName, table, fetchData, zoomLevel }) => {

  const [columnResizeMode, setColumnResizeMode] =
    React.useState<ColumnResizeMode>('onChange');

  const [columnResizeDirection, setColumnResizeDirection] =
    React.useState<ColumnResizeDirection>('ltr');

  const [aiContextArray, setAiContextArray] = React.useState<AiContextObject[]>([]);

  const handleCellClick = (tableName: string, column: string, row: number, value: any) => {
    const newObject: AiContextObject = { tableName, column, row, value };
  
    setAiContextArray((prevArray) => {
      // Check if the object already exists in the array based on column and row
      const exists = ifExists(newObject.column, newObject.row);
      console.log(exists)
      // If it exists, remove it; otherwise, add it to the array
      if (exists) {
        return prevArray.filter(
          (obj) => !(obj.column === newObject.column && obj.row === newObject.row)
        );
      } else {
        return [...prevArray, newObject];
      }

    });
  };

  const ifExists = (column: string, row: number) => {
    return aiContextArray.some(
      (obj) => obj.column === column && obj.row === row
    );
  };
  
  

  const columns = useMemo(() => {
    return Object.keys(table.header).map((key) =>
      columnHelper.accessor(key, {
        header: () => key.charAt(0).toUpperCase() + key.slice(1),
        cell: (info) => info.getValue(),
        enableResizing: true,
      })
    );
  }, [table.header]);

  const data = useMemo(() => table.rows, [table.rows]);

  const reactTable = useReactTable({
    data,
    columns,
    columnResizeMode,
    columnResizeDirection,
    getCoreRowModel: getCoreRowModel(),
  });

  useEffect(() => {
    console.log(aiContextArray)
  }, [aiContextArray])

  return (
    <div className="table-container">
      <div style={{ direction: reactTable.options.columnResizeDirection }}>
        <table
          style={{
            transform: `scale(${zoomLevel})`,
            transformOrigin: 'top left',
            width: reactTable.getCenterTotalSize(),
          }}
        >
          <thead>
            {reactTable.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    colSpan={header.colSpan}
                    style={{
                      width: header.getSize(),
                      position: 'relative',
                    }}
                  >
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                    <div
                      {...{
                        onDoubleClick: () => header.column.resetSize(),
                        onMouseDown: header.getResizeHandler(),
                        onTouchStart: header.getResizeHandler(),
                        className: `tbl_resizer ${
                          reactTable.options.columnResizeDirection
                        } ${
                          header.column.getIsResizing() ? 'isResizing' : ''
                        }`,
                        style: {
                          transform:
                            columnResizeMode === 'onEnd' &&
                            header.column.getIsResizing()
                              ? `translateX(${
                                  (reactTable.options.columnResizeDirection ===
                                  'rtl'
                                    ? -1
                                    : 1) *
                                  (reactTable.getState().columnSizingInfo
                                    .deltaOffset ?? 0)
                                }px)`
                              : '',
                        },
                      }}
                    />
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {reactTable.getRowModel().rows.map((row) => (
              <tr key={row.id}>
                {row.getVisibleCells().map((cell) => {
                  const header = reactTable
                    .getHeaderGroups()[0]
                    .headers.find((h) => h.column.id === cell.column.id);

                  return (
                    <td
                      key={cell.id}
                      onClick={() => handleCellClick( tableName, cell.column.id, row.index, cell.getValue())}
                      style={{
                        width: cell.column.getSize(),
                        position: 'relative',
                        backgroundColor: ifExists(cell.column.id, row.index) ? '#F8B195' : 'white',
                      }}
                    >
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      <div
                        {...{
                          onDoubleClick: header?.column.resetSize,
                          onMouseDown: header?.getResizeHandler(),
                          onTouchStart: header?.getResizeHandler(),
                          className: `tbl_resizer ${reactTable.options.columnResizeDirection} ${
                            header?.column.getIsResizing() ? 'isResizing' : ''
                          }`,
                          style: {
                            position: 'absolute',
                            top: 0,
                            right: reactTable.options.columnResizeDirection === 'ltr' ? 0 : 'auto',
                            left: reactTable.options.columnResizeDirection === 'rtl' ? 0 : 'auto',
                            height: '100%',
                            width: '5px',
                            backgroundColor: header?.column.getIsResizing() ? 'blue' : 'rgba(0, 0, 0, 0.5)',
                            cursor: 'col-resize',
                            userSelect: 'none',
                            touchAction: 'none',
                            opacity: header?.column.getIsResizing() ? 1 : 0,
                          },
                        }}
                      />
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default TenstackTable;
