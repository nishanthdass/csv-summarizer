/**
 * Alters the column ID by adding a table-specific prefix.
 * @param tableName - The name of the current table.
 * @param columnKey - The key of the column.
 * @returns The altered column ID.
 */
export const alterId = (tableName: string, columnKey: string): string => {
    return `${tableName}_${columnKey}`;
  };
  
  /**
   * Reverts the altered column ID back to its original column key.
   * @param id - The altered column ID (e.g., tableName_columnKey).
   * @param tableName - The name of the current table.
   * @returns The original column key.
   */
export const revertId = (id: string, tableName: string): string => {
    if (id.startsWith(`${tableName}_`)) {
      return id.slice(`${tableName}_`.length); // Remove the tableName and underscore prefix
    }
    return id; // If it doesn't match, return the id as is
  };
  