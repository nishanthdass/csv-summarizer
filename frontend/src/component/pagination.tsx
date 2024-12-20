
import React, { useState, useCallback } from 'react';
import doubleLeft from '../assets/double-left.png';
import left from '../assets/left.png';
import right from '../assets/right.png';
import doubleRight from '../assets/double-right.png';
import zoom from '../assets/plus-small.png';
import zoomOut from '../assets/minus-small.png';
import resetZoom from '../assets/reset-zoom.png';
import { useDataContext } from '../context/useDataContext';
import { useTableUploadSelect } from '../hooks/useTableUploadSelect';
import { useUIContext } from '../context/useUIcontext';

const Pagination = () => {
  const { currentTable } = useDataContext();
  const { tableZoomLevel, settableZoomLevel } = useUIContext();
  const { loadTableFromDatabase } = useTableUploadSelect();

  
  const handleZoomIn = useCallback(() => {
    if (currentTable?.name) {
      settableZoomLevel((prevZoomLevels) => ({
        ...prevZoomLevels,
        [currentTable.name]: Math.min((prevZoomLevels[currentTable.name] || 1) + 0.1, 2),
      }));
    }
  }, [currentTable, settableZoomLevel]);
  
  const handleZoomOut = useCallback(() => {
    if (currentTable?.name) {
      settableZoomLevel((prevZoomLevels) => ({
        ...prevZoomLevels,
        [currentTable.name]: Math.max((prevZoomLevels[currentTable.name] || 1) - 0.1, 0.5),
      }));
    }
  }, [currentTable, settableZoomLevel]);
  
  const handleResetZoom = useCallback(() => {
    if (currentTable?.name) {
      settableZoomLevel((prevZoomLevels) => ({
        ...prevZoomLevels,
        [currentTable.name]: 1,
      }));
    }
  }, [currentTable, settableZoomLevel]);
  
  

  const handlePageChange = async (newPage: number | undefined) => {
    if (newPage === undefined || !currentTable || newPage === currentTable.data.page) return;

    if (currentTable) {
      await loadTableFromDatabase(currentTable.name, newPage, currentTable.data.page_size);
    }
  };

  const handlePageSizeChange = async (newPageSize: number | undefined) => {
    if (!currentTable) return;

    if (currentTable) {
      await loadTableFromDatabase(currentTable.name, currentTable.data.page, newPageSize);
    }
  };

  if (!loadTableFromDatabase) return null;

  return (
    <div style={{ marginTop: '10px', display: 'flex', justifyContent: 'space-between' }}>
      {/* Zoom Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
        <button className="pagination-button" onClick={handleZoomOut}>
          <img src={zoomOut} alt="Zoom Out" />
        </button>
        <button className="pagination-button small" onClick={handleResetZoom}>
          <img src={resetZoom} alt="Reset Zoom" />
        </button>
        <button className="pagination-button" onClick={handleZoomIn}>
          <img src={zoom} alt="Zoom In" />
        </button>
      </div>

      {/* Pagination Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
        <button
          className="pagination-button"
          onClick={() => handlePageChange(1)}
          disabled={currentTable?.data.page === 1}
        >
          <img src={doubleLeft} alt="First Page" />
        </button>
        <button
          className="pagination-button"
          onClick={() => handlePageChange((currentTable?.data.page || 1)- 1)}
          disabled={currentTable?.data.page === 1}
        >
          <img src={left} alt="Previous Page" />
        </button>
        <span>
          Page{' '}
          <input
            type="number"
            min="1"
            value={currentTable?.data.page}
            onChange={(e) => handlePageChange(Number(e.target.value))}
            style={{ width: '40px' }}
          />{' '}
          of {currentTable?.data.total_pages}
        </span>
        <button
          className="pagination-button"
          onClick={() => handlePageChange((currentTable?.data.page || 1)+ 1)}
          disabled={currentTable?.data.page === currentTable?.data.total_pages}
        >
          <img src={right} alt="Next Page" />
        </button>
        <button
          className="pagination-button"
          onClick={() => handlePageChange(currentTable?.data.total_pages)}
          disabled={currentTable?.data.page === currentTable?.data.total_pages}
        >
          <img src={doubleRight} alt="Last Page" />
        </button>
      </div>
      {/* Page Size Selector */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
        Show{' '}
        <select value={currentTable?.data.page_size} onChange={(e) => handlePageSizeChange(Number(e.target.value))}>
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

