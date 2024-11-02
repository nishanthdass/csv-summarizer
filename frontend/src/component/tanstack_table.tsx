import React, { useMemo, useEffect } from 'react';
import { TenstackTableProps } from '../utilities/types';
import { useAiContext } from '../hooks/useAiContext';
import { isRowFullySelected } from '../hooks/useAiContext';

import {
  useReactTable,
  ColumnResizeMode,
  createColumnHelper,
  getCoreRowModel,
  flexRender,
  ColumnResizeDirection,
} from '@tanstack/react-table';

const columnHelper = createColumnHelper<any>();

const TenstackTable: React.FC<TenstackTableProps> = ({ tableName, table, fetchData, zoomLevel }) => {
  const [columnResizeMode, setColumnResizeMode] = React.useState<ColumnResizeMode>('onChange');
  const [columnResizeDirection, setColumnResizeDirection] = React.useState<ColumnResizeDirection>('ltr');

  const { aiContextArray, handleCellClick, ifExists } = useAiContext({
    tableName,
    tableRows: table.rows,
  });

  const columns = useMemo(() => {
    const rowNumberColumn = columnHelper.display({
      id: 'rowNumber',
      header: '#',
      cell: (info) => info.row.index + (table.page - 1) * table.page_size + 1,
      enableResizing: false,
      size: 0,
    });

    const dataColumns = Object.keys(table.header).map((key) =>
      columnHelper.accessor(key, {
        header: () => key.charAt(0).toUpperCase() + key.slice(1),
        cell: (info) => info.getValue(),
        enableResizing: true,
      })
    );

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
    console.log(aiContextArray);
  }, [aiContextArray]);

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
                      : flexRender(header.column.columnDef.header, header.getContext())}
                    {header.index !== 0 && (
                      <div
                        onDoubleClick={() => header.column.resetSize()}
                        onMouseDown={header.getResizeHandler()}
                        onTouchStart={header.getResizeHandler()}
                        className={`tbl_resizer ${reactTable.options.columnResizeDirection} ${
                          header.column.getIsResizing() ? 'isResizing' : ''
                        }`}
                        style={{
                          transform:
                            columnResizeMode === 'onEnd' && header.column.getIsResizing()
                              ? `translateX(${
                                  (reactTable.options.columnResizeDirection === 'rtl' ? -1 : 1) *
                                  (reactTable.getState().columnSizingInfo.deltaOffset ?? 0)
                                }px)`
                              : '',
                        }}
                      />
                    )}
                  </th>
                ))}
              </tr>
            ))}
          </thead>

          <tbody>
            {reactTable.getRowModel().rows.map((row) => {
              const rowIndex = row.index;
              const isRowSelected = isRowFullySelected(rowIndex, aiContextArray, reactTable, tableName);

              return (
                <tr key={row.id}>
                  {row.getVisibleCells().map((cell) => {
                    const columnId = cell.column.id;
                    const isRowNumberColumn = columnId === 'rowNumber';
                    const isCellSelected = ifExists(columnId, rowIndex) && !isRowNumberColumn;

                    const cellClassName = isCellSelected
                      ? 'selected-cell'
                      : isRowSelected
                      ? 'selected-row'
                      : isRowNumberColumn
                      ? 'row-number-cell'
                      : rowIndex % 2 === 0
                      ? 'even-row'
                      : 'odd-row';

                    const header = reactTable
                      .getHeaderGroups()[0]
                      .headers.find((h) => h.column.id === columnId);

                    return (
                      <td
                        key={cell.id}
                        onClick={() => handleCellClick(columnId, rowIndex, cell.getValue(), isRowNumberColumn)}
                        className={cellClassName}
                        style={{
                          width: cell.column.getSize(),
                          position: 'relative',
                          textAlign: 'center',
                          padding: '0 4px',
                          cursor: isRowNumberColumn ? 'pointer' : 'default',
                        }}
                      >
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        <div
                          onDoubleClick={header?.column.resetSize}
                          onMouseDown={header?.getResizeHandler()}
                          onTouchStart={header?.getResizeHandler()}
                          className={`tbl_resizer ${reactTable.options.columnResizeDirection} ${
                            header?.column.getIsResizing() ? 'isResizing' : ''
                          }`}
                          style={{
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
                          }}
                        />
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default TenstackTable;
