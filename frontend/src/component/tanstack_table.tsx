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

  const handleCellClick = (tableName: string, column: string, row: number, value: any, isRowNumberColumn: boolean) => {

    console.log(tableName, column, row, value, isRowNumberColumn)
    const newObject: AiContextObject = { tableName, column, row, value };
  
    setAiContextArray((prevArray) => {
      // Check if the object already exists in the array based on column and row
      const exists = ifExists(newObject.tableName, newObject.column, newObject.row);
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

  const ifExists = (tableName: string, column: string, row: number) => {
    return aiContextArray.some(
      (obj) => obj.column === column && obj.row === row && obj.tableName === tableName
    );
  };

  const columns = useMemo(() => {
    // Helper column for Row Number
    const rowNumberColumn = columnHelper.display({
      id: 'rowNumber',  // Unique identifier for the column
      header: '#',  // Column header label
      cell: (info) => info.row.index + ((table.page - 1) * table.page_size) + 1,  // Render row number based on index, starting from 1
      enableResizing: false,
      size: 0,  // Set the size of the column to 0 to hide it
    });
  
    // Map over the header keys to generate columns for each field
    const dataColumns = Object.keys(table.header).map((key) =>
      columnHelper.accessor(key, {
        header: () => key.charAt(0).toUpperCase() + key.slice(1),
        cell: (info) => info.getValue(),
        enableResizing: true,
      })
    );
  
    // Include the Row Number column as the first column
    return [rowNumberColumn, ...dataColumns];
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
                  className={header.index === 0 ? 'row-number-cell' : ''}
                  colSpan={header.colSpan}
                  style={{
                    backgroundColor: '#E0E0E0',
                    width: header.getSize(),
                    position: 'relative',
                    textAlign: 'center',
                  }}
                >
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                    {/* Conditionally add resizer div only if it's not the row number column */}
                    {header.index !== 0 && (
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
                                    (reactTable.options.columnResizeDirection === 'rtl'
                                      ? -1
                                      : 1) *
                                    (reactTable.getState().columnSizingInfo.deltaOffset ?? 0)
                                  }px)`
                                : '',
                          },
                        }}
                      />
                    )}
                  </th>
                ))}
              </tr>
            ))}
          </thead>

          <tbody>
            {reactTable.getRowModel().rows.map((row) => (
              <tr key={row.id}>
                {row.getVisibleCells().map((cell, index) => {
                  const isRowNumberColumn = index === 0;
                  const header = reactTable
                    .getHeaderGroups()[0]
                    .headers.find((h) => h.column.id === cell.column.id);

                  return (
                      <td
                        key={cell.id}
                        onClick={() => handleCellClick(tableName, cell.column.id, row.index, cell.getValue(), isRowNumberColumn)}
                        style={{
                          width: cell.column.getSize(),
                          position: 'relative',
                          backgroundColor: 
                          ifExists(tableName, cell.column.id, row.index) && !isRowNumberColumn
                            ? '#F8B195'
                            : isRowNumberColumn
                            ? '#E0E0E0'
                            : row.index % 2 === 0
                            ? '#F5F5F5'
                            : 'white',
                          textAlign: 'center',
                          padding: '0 4px',  // Minimal padding to fit the number tightly
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
