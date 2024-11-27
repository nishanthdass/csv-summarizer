
import React from 'react';
import doubleLeft from '../assets/double-left.png';
import left from '../assets/left.png';
import right from '../assets/right.png';
import doubleRight from '../assets/double-right.png';
import zoom from '../assets/plus-small.png';
import zoomOut from '../assets/minus-small.png';
import resetZoom from '../assets/reset-zoom.png';
import { useDataContext } from '../context/useDataContext';
import { table } from 'console';

interface PaginationProps {
  onZoomIn: () => void;
  onZoomOut: () => void;
  onResetZoom: () => void;
}

const Pagination: React.FC<PaginationProps> = ({ onZoomIn, onZoomOut, onResetZoom }) => {
  const { currentTable, tableData, setTableData, loadTableData, } = useDataContext();


  const handlePageChange = async (newPage: number) => {
    if (!tableData || newPage === tableData.page || typeof currentTable !== 'string') return;

    // Update the page in the state and fetch new data
    setTableData((prev) => ({
      ...prev!,
      page: newPage,
    }));

    if (currentTable) {
      await loadTableData(currentTable, newPage, tableData.page_size);
    }
  };

  const handlePageSizeChange = async (newPageSize: number) => {
    if (!tableData) return;

    // Update the page size in the state and fetch new data
    setTableData((prev) => ({
      ...prev!,
      page_size: newPageSize,
    }));
    if (currentTable) {
      await loadTableData(currentTable, tableData.page, newPageSize);
    }
  };

  if (!tableData) return null;

  return (
    <div style={{ marginTop: '10px', display: 'flex', justifyContent: 'space-between' }}>
      {/* Zoom Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
        <button className="pagination-button" onClick={onZoomOut}>
          <img src={zoomOut} alt="Zoom Out" />
        </button>
        <button className="pagination-button small" onClick={onResetZoom}>
          <img src={resetZoom} alt="Reset Zoom" />
        </button>
        <button className="pagination-button" onClick={onZoomIn}>
          <img src={zoom} alt="Zoom In" />
        </button>
      </div>

      {/* Pagination Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
        <button
          className="pagination-button"
          onClick={() => handlePageChange(1)}
          disabled={tableData.page === 1}
        >
          <img src={doubleLeft} alt="First Page" />
        </button>
        <button
          className="pagination-button"
          onClick={() => handlePageChange(tableData.page - 1)}
          disabled={tableData.page === 1}
        >
          <img src={left} alt="Previous Page" />
        </button>
        <span>
          Page{' '}
          <input
            type="number"
            min="1"
            value={tableData.page}
            onChange={(e) => handlePageChange(Number(e.target.value))}
            style={{ width: '40px' }}
          />{' '}
          of {tableData.total_pages}
        </span>
        <button
          className="pagination-button"
          onClick={() => handlePageChange(tableData.page + 1)}
          disabled={tableData.page === tableData.total_pages}
        >
          <img src={right} alt="Next Page" />
        </button>
        <button
          className="pagination-button"
          onClick={() => handlePageChange(tableData.total_pages)}
          disabled={tableData.page === tableData.total_pages}
        >
          <img src={doubleRight} alt="Last Page" />
        </button>
      </div>
      {/* Page Size Selector */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
        Show{' '}
        <select value={tableData.page_size} onChange={(e) => handlePageSizeChange(Number(e.target.value))}>
          {[10, 20, 30, 40, 50].map((size) => (
            <option key={size} value={size}>
              {size}
            </option>
          ))}
        </select>{' '}
        rows per page
      </div>
    </div>
  );
};

export default Pagination;
