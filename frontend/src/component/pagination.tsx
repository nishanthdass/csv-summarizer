import React from 'react';
import doubleLeft from '../assets/double-left.png';
import left from '../assets/left.png';
import right from '../assets/right.png';
import doubleRight from '../assets/double-right.png';
import zoom from '../assets/plus-small.png';
import zoomOut from '../assets/minus-small.png';
import resetZoom from '../assets/reset-zoom.png';

interface PaginationProps {
  currentPage: number;
  pageSize: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onResetZoom: () => void;
}

const Pagination: React.FC<PaginationProps> = ({
  currentPage,
  pageSize,
  totalPages,
  onPageChange,
  onPageSizeChange,
  onZoomIn,
  onZoomOut,
  onResetZoom,
}) => {
  const handlePreviousPage = () => {
    if (currentPage > 1) {
      onPageChange(currentPage - 1);
    }
  };

  const handleNextPage = () => {
    if (currentPage < totalPages) {
      onPageChange(currentPage + 1);
    }
  };

  const handleFirstPage = () => {
    if (currentPage > 1) {
      onPageChange(1);
    }
  };

  const handleLastPage = () => {
    if (currentPage < totalPages) {
      onPageChange(totalPages);
    }
  };

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
          onClick={handleFirstPage}
          disabled={currentPage === 1}
        >
          <img
            src={doubleLeft}
            alt="First Page"
            style={{ opacity: currentPage === 1 ? 0.3 : 1 }}
          />
        </button>
        <button
          className="pagination-button"
          onClick={handlePreviousPage}
          disabled={currentPage === 1}
        >
          <img
            src={left}
            alt="Previous Page"
            style={{ opacity: currentPage === 1 ? 0.3 : 1 }}
          />
        </button>
        <span style={{ margin: '0 10px' }}>
          Page{' '}
          <input
            type="number"
            value={currentPage}
            onChange={(e) => onPageChange(Number(e.target.value))}
            style={{ width: '40px' }}
          />{' '}
          of {totalPages}
        </span>
        <button
          className="pagination-button"
          onClick={handleNextPage}
          disabled={currentPage === totalPages}
        >
          <img
            src={right}
            alt="Next Page"
            style={{ opacity: currentPage === totalPages ? 0.3 : 1 }}
          />
        </button>
        <button
          className="pagination-button"
          onClick={handleLastPage}
          disabled={currentPage === totalPages}
        >
          <img
            src={doubleRight}
            alt="Last Page"
            style={{ opacity: currentPage === totalPages ? 0.3 : 1 }}
          />
        </button>
      </div>

      {/* Page Size Selector */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
        Show{' '}
        <select value={pageSize} onChange={(e) => onPageSizeChange(Number(e.target.value))}>
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
