
import React, { useState, useCallback, useEffect } from 'react';
import { useDataContext } from '../context/useDataContext';


const PdfViewer = () => {
    const { currentPdf } = useDataContext();

    return (
            <div className="pdf-container">
                {currentPdf && (
                    <embed src={currentPdf.data.url} width="100%" height="100%" type="application/pdf" />
                )} 
            </div>
            );

}

export default PdfViewer