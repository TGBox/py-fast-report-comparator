program FrxRender;

{ Renders a FastReport VCL template (.fr3) with the real engine into a PDF.

  Usage: FrxRender.exe <template.fr3> <fake-data.db> <output.pdf>

  All TfrxFDQuery objects stay in the report (scripts may reference them), but they are
  connected to the SQLite file written by py-fast-report-comparator and their SQL is
  replaced by "SELECT * FROM <query name>". No PostgreSQL, no real patient data.
  On failure the exit code is 1 and the message is written to <output.pdf>.error.txt. }

{$APPTYPE CONSOLE}

uses
  System.SysUtils,
  System.Classes,
  System.IOUtils,
  Vcl.Forms,
  Data.DB,
  FireDAC.Stan.Intf,
  FireDAC.Stan.Option,
  FireDAC.Stan.Def,
  FireDAC.Stan.Async,
  FireDAC.Stan.ExprFuncs,
  FireDAC.DApt,
  FireDAC.Phys,
  FireDAC.Phys.SQLite,
  FireDAC.Phys.SQLiteDef,
  FireDAC.Phys.SQLiteWrapper.Stat,
  FireDAC.ConsoleUI.Wait,
  FireDAC.Comp.Client,
  frxClass,
  frxFDComponents,
  frxExportPDF,
  frxTableObject,
  frxBarcode,
  frxChBox,
  frxCross,
  frxGradient,
  frxRich,
  frxDCtrl,
  frxChart,
  FastReportAddFunctions in '..\..\..\cur-delphi\Library\FastReportAddFunctions.pas';

function QuoteIdent(const S: string): string;
begin
  Result := '"' + StringReplace(S, '"', '""', [rfReplaceAll]) + '"';
end;

procedure DefineVariable(Report: TfrxReport; const Name: string);
begin
  // The PVS passes these at print time; empty values keep scripts like get('ids') working.
  if Report.Variables.IndexOf(Name) = -1 then
    Report.Variables[Name] := '''''';
end;

procedure UseFakeData(Report: TfrxReport; Connection: TFDConnection);
var
  i, j: Integer;
  Query: TfrxFDQuery;
  Sql: string;
begin
  for i := 0 to Report.AllObjects.Count - 1 do
    if TObject(Report.AllObjects[i]) is TfrxFDQuery then
    begin
      Query := TfrxFDQuery(Report.AllObjects[i]);
      Query.Query.Connection := Connection;
      Sql := 'SELECT * FROM ' + QuoteIdent(Query.Name);
      // Keep every parameter in the SQL so scripts and expressions can still set it.
      for j := 0 to Query.Params.Count - 1 do
        if j = 0 then
          Sql := Sql + ' WHERE (:' + Query.Params[j].Name + ' IS NULL OR 1 = 1)'
        else
          Sql := Sql + ' AND (:' + Query.Params[j].Name + ' IS NULL OR 1 = 1)';
      Query.SQL.Text := Sql;
    end;
end;

procedure Render(const TemplateFile, DbFile, PdfFile: string);
var
  Connection: TFDConnection;
  Components: TfrxFDComponents;
  Report: TfrxReport;
  Pdf: TfrxPDFExport;
begin
  Connection := TFDConnection.Create(nil);
  Components := TfrxFDComponents.Create(nil);
  Report := TfrxReport.Create(nil);
  Pdf := TfrxPDFExport.Create(nil);
  try
    Connection.LoginPrompt := False;
    Connection.DriverName := 'SQLite';
    Connection.Params.Values['Database'] := DbFile;
    Connection.Params.Values['OpenMode'] := 'ReadOnly';
    Connection.Connected := True;
    Components.DefaultDatabase := Connection;

    Report.ShowProgress := False;
    Report.EngineOptions.SilentMode := True;
    if not Report.LoadFromFile(TemplateFile) then
      raise Exception.Create('Vorlage konnte nicht geladen werden.');

    DefineVariable(Report, 'ids');
    DefineVariable(Report, 'sql');
    DefineVariable(Report, 'firmenname');
    DefineVariable(Report, 'params');
    UseFakeData(Report, Connection);

    if not Report.PrepareReport then
      raise Exception.Create('Bericht konnte nicht aufbereitet werden: ' + Report.Errors.Text);

    Pdf.ShowDialog := False;
    Pdf.ShowProgress := False;
    Pdf.OpenAfterExport := False;
    Pdf.FileName := PdfFile;
    if not Report.Export(Pdf) then
      raise Exception.Create('PDF-Export fehlgeschlagen.');
  finally
    Pdf.Free;
    Report.Free;
    Components.Free;
    Connection.Free;
  end;
end;

begin
  if ParamCount < 3 then
  begin
    Writeln('Aufruf: FrxRender.exe <vorlage.fr3> <fake-daten.db> <ausgabe.pdf>');
    ExitCode := 2;
    Exit;
  end;
  try
    Render(ParamStr(1), ParamStr(2), ParamStr(3));
  except
    on E: Exception do
    begin
      TFile.WriteAllText(ParamStr(3) + '.error.txt', E.ClassName + ': ' + E.Message,
        TEncoding.UTF8);
      Writeln(ErrOutput, E.Message);
      ExitCode := 1;
    end;
  end;
end.
