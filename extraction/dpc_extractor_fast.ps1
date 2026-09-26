[CmdletBinding()]
param(
    [string]$PathToDir = "C:\path\to\dpc\files",
    [string]$OutputRoot = ".\outputs_ps51_fast",
    [string]$TargetSheet = ".\pt_list.csv",
    [string]$DpcFileEncoding = "cp932",
    [string]$Delimiter = "`t",
    [int]$MarginDays = 90,

    # 速度優先の推奨値
    [int]$WriteChunkSize = 4000,
    [int]$ReadBufferSize = 1048576,   # 1MB
    [int]$WriteBufferSize = 1048576   # 1MB
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"

if ($null -eq $Delimiter -or $Delimiter.Length -ne 1) {
    throw "この高速版では Delimiter は1文字のみ対応です。例: `t , ; |"
}

function Get-TextEncoding {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [switch]$ForWrite
    )

    switch ($Name.ToLowerInvariant()) {
        "cp932"      { return [System.Text.Encoding]::GetEncoding(932) }
        "shift_jis"  { return [System.Text.Encoding]::GetEncoding(932) }
        "euc_jp"     { return [System.Text.Encoding]::GetEncoding(20932) }
        "iso2022_jp" { return [System.Text.Encoding]::GetEncoding(50220) }
        "utf-8-sig"  {
            if ($ForWrite) { return New-Object System.Text.UTF8Encoding($true) }
            return New-Object System.Text.UTF8Encoding($true, $false)
        }
        "utf-8"      {
            if ($ForWrite) { return New-Object System.Text.UTF8Encoding($false) }
            return New-Object System.Text.UTF8Encoding($false, $false)
        }
        "utf-16"     { return [System.Text.Encoding]::Unicode }
        "utf-32"     { return [System.Text.Encoding]::UTF32 }
        "latin-1"    { return [System.Text.Encoding]::GetEncoding("iso-8859-1") }
        default      { return [System.Text.Encoding]::GetEncoding($Name) }
    }
}

function Get-SubDirNameFast {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath
    )

    $name = [System.IO.Path]::GetFileNameWithoutExtension($FilePath)
    $parts = $name.Split('_')
    if ($parts.Length -lt 3) {
        return "xxxx"
    }
    return $parts[2]
}

function Collect-TargetFilesFast {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RootDir
    )

    $list = New-Object 'System.Collections.Generic.List[string]'
    $regex = New-Object System.Text.RegularExpressions.Regex(
        '^(EFn|FF1|EFg)_.+\.txt$',
        ([System.Text.RegularExpressions.RegexOptions]::Compiled -bor [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    )

    foreach ($path in [System.IO.Directory]::EnumerateFiles($RootDir, "*", [System.IO.SearchOption]::AllDirectories)) {
        $name = [System.IO.Path]::GetFileName($path)
        if ($name.EndsWith(".txt", [System.StringComparison]::OrdinalIgnoreCase) -and $regex.IsMatch($name)) {
            $list.Add($path)
        }
    }
    return $list | Sort-Object
}

$source = @'
using System;
using System.IO;
using System.Text;
using System.Linq;
using System.Globalization;
using System.Collections.Generic;
using System.Text.RegularExpressions;

namespace FastDpc51
{
    public sealed class PtRecord
    {
        public string ResearchId;
        public HashSet<string> YymmSet;
    }

    public sealed class ProcessResult
    {
        public long LineCount;
        public long ExtractedRows;
        public int OutputFiles;
        public long MalformedRows;
    }

    internal sealed class OutputState : IDisposable
    {
        public readonly StreamWriter Writer;
        public readonly List<string> Buffer;

        public OutputState(StreamWriter writer, int capacity)
        {
            Writer = writer;
            Buffer = new List<string>(capacity);
        }

        public void Flush()
        {
            for (int i = 0; i < Buffer.Count; i++)
            {
                Writer.WriteLine(Buffer[i]);
            }
            Buffer.Clear();
        }

        public void Dispose()
        {
            Writer.Dispose();
        }
    }

    public static class Engine
    {
        private static string[] SplitCsvLine(string line, char delimiter)
        {
            List<string> fields = new List<string>(16);
            StringBuilder sb = new StringBuilder(line != null ? line.Length : 0);
            bool inQuotes = false;

            if (line == null)
            {
                fields.Add(string.Empty);
                return fields.ToArray();
            }

            for (int i = 0; i < line.Length; i++)
            {
                char ch = line[i];

                if (ch == '"')
                {
                    if (inQuotes && i + 1 < line.Length && line[i + 1] == '"')
                    {
                        sb.Append('"');
                        i++;
                    }
                    else
                    {
                        inQuotes = !inQuotes;
                    }
                    continue;
                }

                if (!inQuotes && ch == delimiter)
                {
                    fields.Add(sb.ToString());
                    sb.Length = 0;
                    continue;
                }

                sb.Append(ch);
            }

            fields.Add(sb.ToString());
            return fields.ToArray();
        }

        private static HashSet<string> BuildYymmSet(string startText, string endText, int marginBeforeDays, int marginAfterDays)
        {
            DateTime startDate = DateTime.ParseExact(startText, "yyyyMMdd", CultureInfo.InvariantCulture);
            DateTime endDate = DateTime.ParseExact(endText, "yyyyMMdd", CultureInfo.InvariantCulture);

            DateTime left = startDate.AddDays(-marginBeforeDays);
            DateTime right = endDate.AddDays(marginAfterDays);

            int startIdx = (left.Year * 12) + (left.Month - 1);
            int endIdx = (right.Year * 12) + (right.Month - 1);

            HashSet<string> set = new HashSet<string>(StringComparer.Ordinal);
            for (int idx = startIdx; idx <= endIdx; idx++)
            {
                int year = idx / 12;
                int month = (idx % 12) + 1;
                set.Add(string.Format(CultureInfo.InvariantCulture, "{0:D2}{1:D2}", year % 100, month));
            }
            return set;
        }

        public static Dictionary<string, PtRecord> LoadPtList(string path, Encoding encoding, int marginBeforeDays, int marginAfterDays)
        {
            Dictionary<string, PtRecord> map = new Dictionary<string, PtRecord>(StringComparer.Ordinal);
            HashSet<string> researchIds = new HashSet<string>(StringComparer.Ordinal);

            using (FileStream fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read, 65536, FileOptions.SequentialScan))
            using (StreamReader sr = new StreamReader(fs, encoding, true, 65536))
            {
                string line;
                string[] header = null;

                int idxDataIdentifier = -1;
                int idxResearchId = -1;
                int idxEncounterStart = -1;
                int idxEncounterEnd = -1;
                int idxEventDate = -1;

                while ((line = sr.ReadLine()) != null)
                {
                    if (line.Length == 0)
                    {
                        continue;
                    }

                    string[] row = SplitCsvLine(line, ',');

                    if (header == null)
                    {
                        header = row;
                        if (header.Select(h => (h ?? string.Empty).Trim()).Distinct(StringComparer.Ordinal).Count() != header.Length)
                        {
                            throw new InvalidOperationException("pt_list.csv の header に重複列があります");
                        }

                        for (int i = 0; i < header.Length; i++)
                        {
                            string h = (header[i] ?? string.Empty).Trim();
                            if (string.Equals(h, "data_identifier", StringComparison.Ordinal)) idxDataIdentifier = i;
                            else if (string.Equals(h, "research_id", StringComparison.Ordinal)) idxResearchId = i;
                            else if (string.Equals(h, "encounter_start_date", StringComparison.Ordinal)) idxEncounterStart = i;
                            else if (string.Equals(h, "encounter_end_date", StringComparison.Ordinal)) idxEncounterEnd = i;
                            else if (string.Equals(h, "event_date", StringComparison.Ordinal)) idxEventDate = i;
                        }

                        if (idxDataIdentifier < 0 || idxResearchId < 0 || idxEncounterStart < 0 || idxEncounterEnd < 0)
                        {
                            throw new InvalidOperationException("pt_list.csv に必要列がありません。required: data_identifier, research_id, encounter_start_date, encounter_end_date");
                        }

                        continue;
                    }

                    if (row.Length != header.Length)
                    {
                        throw new InvalidOperationException("pt_list.csv の列数が不正です");
                    }

                    string dataIdentifierRaw = idxDataIdentifier < row.Length ? (row[idxDataIdentifier] ?? string.Empty).Trim() : string.Empty;
                    if (!Regex.IsMatch(dataIdentifierRaw, @"\A[0-9]{1,10}\z"))
                    {
                        throw new InvalidOperationException("pt_list.csv の data_identifier が不正です");
                    }
                    string dataIdentifier = dataIdentifierRaw.PadLeft(10, '0');

                    string researchId = idxResearchId < row.Length ? (row[idxResearchId] ?? string.Empty).Trim() : string.Empty;
                    string encounterStart = idxEncounterStart < row.Length ? (row[idxEncounterStart] ?? string.Empty).Trim() : string.Empty;
                    string encounterEnd = idxEncounterEnd < row.Length ? (row[idxEncounterEnd] ?? string.Empty).Trim() : string.Empty;
                    if (!Regex.IsMatch(researchId, @"\A[A-Za-z0-9][A-Za-z0-9_-]*\z"))
                    {
                        throw new InvalidOperationException("pt_list.csv の research_id が不正です");
                    }
                    string reserved = researchId.ToUpperInvariant();
                    if (reserved == "CON" || reserved == "PRN" || reserved == "AUX" || reserved == "NUL" ||
                        Regex.IsMatch(reserved, @"\A(COM|LPT)[1-9]\z"))
                    {
                        throw new InvalidOperationException("pt_list.csv の research_id は予約名です");
                    }
                    if (!Regex.IsMatch(encounterStart, @"\A[0-9]{8}\z") || !Regex.IsMatch(encounterEnd, @"\A[0-9]{8}\z"))
                    {
                        throw new InvalidOperationException("pt_list.csv の対象日付が不正です");
                    }
                    DateTime startDate = DateTime.ParseExact(encounterStart, "yyyyMMdd", CultureInfo.InvariantCulture);
                    DateTime endDate = DateTime.ParseExact(encounterEnd, "yyyyMMdd", CultureInfo.InvariantCulture);
                    if (startDate > endDate)
                    {
                        throw new InvalidOperationException("pt_list.csv の対象期間が逆転しています");
                    }
                    if (idxEventDate >= 0)
                    {
                        string eventDate = (row[idxEventDate] ?? string.Empty).Trim();
                        if (eventDate.Length > 0)
                        {
                            if (!Regex.IsMatch(eventDate, @"\A[0-9]{8}\z"))
                            {
                                throw new InvalidOperationException("pt_list.csv の event_date が不正です");
                            }
                            DateTime.ParseExact(eventDate, "yyyyMMdd", CultureInfo.InvariantCulture);
                        }
                    }
                    if (map.ContainsKey(dataIdentifier) || !researchIds.Add(researchId))
                    {
                        throw new InvalidOperationException("pt_list.csv の識別子が重複しています");
                    }

                    PtRecord rec = new PtRecord();
                    rec.ResearchId = researchId;
                    rec.YymmSet = BuildYymmSet(encounterStart, encounterEnd, marginBeforeDays, marginAfterDays);

                    map.Add(dataIdentifier, rec);
                }
                if (header == null)
                {
                    throw new InvalidOperationException("pt_list.csv が空です");
                }
            }

            return map;
        }

        public static HashSet<string> BuildGlobalYymmSet(Dictionary<string, PtRecord> ptMap)
        {
            HashSet<string> set = new HashSet<string>(StringComparer.Ordinal);
            foreach (PtRecord rec in ptMap.Values)
            {
                foreach (string yymm in rec.YymmSet)
                {
                    set.Add(yymm);
                }
            }
            return set;
        }

        public static bool TryGetSecondField(string line, char delimiter, out string field)
        {
            field = null;
            if (line == null)
            {
                return false;
            }

            bool inQuotes = false;
            int secondStart = -1;

            for (int i = 0; i < line.Length; i++)
            {
                char ch = line[i];

                if (ch == '"')
                {
                    if (inQuotes && i + 1 < line.Length && line[i + 1] == '"')
                    {
                        i++;
                        continue;
                    }
                    inQuotes = !inQuotes;
                    continue;
                }

                if (!inQuotes && ch == delimiter)
                {
                    secondStart = i + 1;
                    break;
                }
            }

            if (secondStart < 0)
            {
                return false;
            }

            inQuotes = false;
            StringBuilder sb = null;
            int chunkStart = secondStart;

            for (int i = secondStart; i < line.Length; i++)
            {
                char ch = line[i];

                if (ch == '"')
                {
                    if (sb == null)
                    {
                        sb = new StringBuilder(Math.Max(16, line.Length - secondStart));
                    }

                    if (i > chunkStart)
                    {
                        sb.Append(line, chunkStart, i - chunkStart);
                    }

                    if (inQuotes && i + 1 < line.Length && line[i + 1] == '"')
                    {
                        sb.Append('"');
                        i++;
                        chunkStart = i + 1;
                        continue;
                    }

                    inQuotes = !inQuotes;
                    chunkStart = i + 1;
                    continue;
                }

                if (!inQuotes && ch == delimiter)
                {
                    if (sb == null)
                    {
                        field = line.Substring(secondStart, i - secondStart);
                    }
                    else
                    {
                        if (i > chunkStart)
                        {
                            sb.Append(line, chunkStart, i - chunkStart);
                        }
                        field = sb.ToString();
                    }
                    return true;
                }
            }

            if (sb == null)
            {
                field = line.Substring(secondStart);
            }
            else
            {
                if (line.Length > chunkStart)
                {
                    sb.Append(line, chunkStart, line.Length - chunkStart);
                }
                field = sb.ToString();
            }

            return true;
        }

        private static bool IsHeaderSecondField(string secondField)
        {
            string normalized = (secondField ?? string.Empty).Trim().Normalize(NormalizationForm.FormKC);
            return string.Equals(normalized, "データ識別番号", StringComparison.Ordinal);
        }

        private static string EscapeCsvField(string value, char delimiter)
        {
            string text = value ?? string.Empty;
            bool needsQuote = text.IndexOfAny(new char[] { delimiter, '"', '\r', '\n' }) >= 0;
            if (!needsQuote)
            {
                return text;
            }
            return "\"" + text.Replace("\"", "\"\"") + "\"";
        }

        private static string ReplaceSecondField(string line, char delimiter, string newSecondField)
        {
            string[] fields = SplitCsvLine(line, delimiter);
            if (fields.Length < 2)
            {
                return line;
            }
            fields[1] = newSecondField ?? string.Empty;
            for (int i = 0; i < fields.Length; i++)
            {
                fields[i] = EscapeCsvField(fields[i], delimiter);
            }
            return string.Join(delimiter.ToString(), fields);
        }

        public static ProcessResult ProcessFile(
            string filePath,
            string fileName,
            string subDirName,
            Dictionary<string, PtRecord> ptMap,
            string outputRoot,
            Encoding inputEncoding,
            Encoding outputEncoding,
            char delimiter,
            int writeChunkSize,
            int readBufferSize,
            int writeBufferSize)
        {
            Dictionary<string, OutputState> outputs = new Dictionary<string, OutputState>(StringComparer.Ordinal);
            ProcessResult result = new ProcessResult();
            string headerLine = null;

            try
            {
                using (FileStream fs = new FileStream(filePath, FileMode.Open, FileAccess.Read, FileShare.Read, readBufferSize, FileOptions.SequentialScan))
                using (StreamReader sr = new StreamReader(fs, inputEncoding, true, readBufferSize))
                {
                    string line;
                    while ((line = sr.ReadLine()) != null)
                    {
                        result.LineCount++;

                        string secondField;
                        if (!TryGetSecondField(line, delimiter, out secondField))
                        {
                            result.MalformedRows++;
                            continue;
                        }

                        if (result.LineCount == 1 && IsHeaderSecondField(secondField))
                        {
                            headerLine = line;
                            continue;
                        }

                        PtRecord rec;
                        if (!ptMap.TryGetValue(secondField, out rec))
                        {
                            continue;
                        }

                        if (!rec.YymmSet.Contains(subDirName))
                        {
                            continue;
                        }

                        string outPath = Path.Combine(outputRoot, rec.ResearchId, subDirName, fileName);
                        OutputState state;
                        if (!outputs.TryGetValue(outPath, out state))
                        {
                            string parent = Path.GetDirectoryName(outPath);
                            if (!Directory.Exists(parent))
                            {
                                Directory.CreateDirectory(parent);
                            }

                            FileStream outFs = new FileStream(outPath, FileMode.Create, FileAccess.Write, FileShare.Read, writeBufferSize, FileOptions.None);
                            StreamWriter sw = new StreamWriter(outFs, outputEncoding, writeBufferSize);
                            sw.NewLine = "\r\n";

                            state = new OutputState(sw, Math.Max(8, writeChunkSize + 4));
                            outputs.Add(outPath, state);
                            result.OutputFiles++;

                            if (headerLine != null)
                            {
                                state.Buffer.Add(headerLine);
                            }

                        }

                        state.Buffer.Add(ReplaceSecondField(line, delimiter, rec.ResearchId));
                        result.ExtractedRows++;

                        if (state.Buffer.Count >= writeChunkSize)
                        {
                            state.Flush();
                        }
                    }
                }
            }
            finally
            {
                foreach (OutputState state in outputs.Values)
                {
                    state.Flush();
                    state.Dispose();
                }
            }

            return result;
        }

        public static void WriteSummaryCsv(Dictionary<string, PtRecord> ptMap, string outputRoot, string summaryPath, Encoding encoding)
        {
            string dir = Path.GetDirectoryName(summaryPath);
            if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
            {
                Directory.CreateDirectory(dir);
            }

            HashSet<string> uniqueResearchIds = new HashSet<string>(StringComparer.Ordinal);
            foreach (PtRecord rec in ptMap.Values)
            {
                if (!string.IsNullOrEmpty(rec.ResearchId))
                {
                    uniqueResearchIds.Add(rec.ResearchId);
                }
            }

            List<string> researchIds = new List<string>(uniqueResearchIds);
            researchIds.Sort(delegate (string a, string b)
            {
                return string.CompareOrdinal(a, b);
            });

            using (FileStream fs = new FileStream(summaryPath, FileMode.Create, FileAccess.Write, FileShare.Read, 65536, FileOptions.None))
            using (StreamWriter sw = new StreamWriter(fs, encoding, 65536))
            {
                sw.NewLine = "\r\n";
                sw.WriteLine("research_id,FF1,EFn,EFg");

                foreach (string researchId in researchIds)
                {
                    string baseDir = Path.Combine(outputRoot, researchId);
                    int ff1 = 0;
                    int efn = 0;
                    int efg = 0;

                    if (Directory.Exists(baseDir))
                    {
                        foreach (string path in Directory.EnumerateFiles(baseDir, "*.txt", SearchOption.AllDirectories))
                        {
                            string name = Path.GetFileName(path);
                            if (name.StartsWith("FF1_", StringComparison.OrdinalIgnoreCase))
                            {
                                ff1++;
                            }
                            else if (name.StartsWith("EFn_", StringComparison.OrdinalIgnoreCase))
                            {
                                efn++;
                            }
                            else if (name.StartsWith("EFg_", StringComparison.OrdinalIgnoreCase))
                            {
                                efg++;
                            }
                        }
                    }

                    sw.WriteLine(string.Format(CultureInfo.InvariantCulture, "{0},{1},{2},{3}", researchId, ff1, efn, efg));
                }
            }
        }
    }
}
'@

if (-not ("FastDpc51.Engine" -as [type])) {
    Add-Type -TypeDefinition $source -Language CSharp
}

$startedAt = Get-Date

$rootDir = [System.IO.Path]::GetFullPath($PathToDir)
$outputRootFull = [System.IO.Path]::GetFullPath($OutputRoot)
$targetSheetFull = [System.IO.Path]::GetFullPath($TargetSheet)

$inputEncoding = Get-TextEncoding -Name $DpcFileEncoding
$outputEncoding = Get-TextEncoding -Name $DpcFileEncoding -ForWrite
$summaryEncoding = Get-TextEncoding -Name "utf-8-sig" -ForWrite
$delimiterChar = $Delimiter[0]

Write-Host ("pt_list を読み込み中: {0}" -f $targetSheetFull)
$ptMap = [FastDpc51.Engine]::LoadPtList($targetSheetFull, $inputEncoding, $MarginDays, $MarginDays)
$globalYymm = [FastDpc51.Engine]::BuildGlobalYymmSet($ptMap)

Write-Host ("対象ファイルを列挙中: {0}" -f $rootDir)
$allFiles = @(Collect-TargetFilesFast -RootDir $rootDir)

$matchedFiles = New-Object 'System.Collections.Generic.List[string]'
foreach ($file in $allFiles) {
    $yymm = Get-SubDirNameFast -FilePath $file
    if ($yymm.Length -ge 4 -and $globalYymm.Contains($yymm.Substring(0, 4))) {
        $matchedFiles.Add($file)
    }
}

$totalFiles = $matchedFiles.Count
if ($totalFiles -eq 0) {
    Write-Host "対象ファイルは見つかりませんでした。"
    return
}

Write-Host ("対象ファイル数: {0:N0}" -f $totalFiles)

$totalLines = [int64]0
$totalExtracted = [int64]0
$totalOutputFiles = 0
$totalMalformedRows = [int64]0
$errorFiles = New-Object System.Collections.ArrayList

$fileIndex = 0
foreach ($file in $matchedFiles) {
    $fileIndex++
    $subDirName = Get-SubDirNameFast -FilePath $file
    $fileName = [System.IO.Path]::GetFileName($file)

    Write-Host ""
    Write-Host ("開始 [{0}/{1}] {2}" -f $fileIndex, $totalFiles, $file)

    try {
        $result = [FastDpc51.Engine]::ProcessFile(
            $file,
            $fileName,
            $subDirName,
            $ptMap,
            $outputRootFull,
            $inputEncoding,
            $outputEncoding,
            $delimiterChar,
            $WriteChunkSize,
            $ReadBufferSize,
            $WriteBufferSize
        )

        $totalLines += [int64]$result.LineCount
        $totalExtracted += [int64]$result.ExtractedRows
        $totalOutputFiles += [int]$result.OutputFiles
        $totalMalformedRows += [int64]$result.MalformedRows

        Write-Host (
            "完了 | 行数 {0:N0} | 抽出 {1:N0} | 出力ファイル {2:N0} | malformed {3:N0}" -f
            $result.LineCount,
            $result.ExtractedRows,
            $result.OutputFiles,
            $result.MalformedRows
        )
    }
    catch {
        Write-Host ("エラー: {0} -> {1}" -f $file, $_.Exception.Message)
        [void]$errorFiles.Add(@{
            file_path = $file
            message = $_.Exception.Message
        })
    }
}

$summaryPath = Join-Path $outputRootFull "summary.csv"
[FastDpc51.Engine]::WriteSummaryCsv($ptMap, $outputRootFull, $summaryPath, $summaryEncoding)

$elapsed = (Get-Date) - $startedAt

Write-Host ""
Write-Host "===== 全体サマリ ====="
Write-Host ("対象ファイル数      : {0:N0}" -f $totalFiles)
Write-Host ("総処理行数          : {0:N0}" -f $totalLines)
Write-Host ("総抽出行数          : {0:N0}" -f $totalExtracted)
Write-Host ("総出力ファイル数    : {0:N0}" -f $totalOutputFiles)
Write-Host ("不正行/短すぎる行数 : {0:N0}" -f $totalMalformedRows)
Write-Host ("エラーファイル数    : {0:N0}" -f $errorFiles.Count)
Write-Host ("サマリーCSV         : {0}" -f $summaryPath)
Write-Host ("合計処理時間        : {0}" -f $elapsed)

if ($errorFiles.Count -gt 0) {
    Write-Host ""
    Write-Host "===== エラー一覧 ====="
    foreach ($e in $errorFiles) {
        Write-Host ("{0} -> {1}" -f $e.file_path, $e.message)
    }
}

return @{
    total_files = $totalFiles
    total_lines = $totalLines
    total_extracted = $totalExtracted
    total_output_files = $totalOutputFiles
    total_malformed_rows = $totalMalformedRows
    error_files = @($errorFiles)
    summary_path = $summaryPath
    elapsed = $elapsed.ToString()
    output_root = $outputRootFull
}
