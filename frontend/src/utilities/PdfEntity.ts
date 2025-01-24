export type PdfData = {
  file_name: string;
  url: string;
};

export default class PdfEntity {
  name: string;
  data: PdfData;

  constructor(name: string, file_name: string) {
    this.name = name;
    this.data = {
      file_name: file_name,
      url: `http://localhost:8000/get-pdf/${encodeURIComponent(name)}`
    };
  }
}
