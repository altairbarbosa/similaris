using System.Diagnostics;
using System.Text;
using System.Text.RegularExpressions;
using Similaris.WinUI.Models;

namespace Similaris.WinUI.Services;

public sealed class PythonCoreRunner
{
    private static readonly Regex PercentagePattern = new(@"(?:\(|\b)(\d+(?:[\.,]\d+)?)%(?:\)|\b)", RegexOptions.Compiled);
    private static readonly Regex CountPattern = new(@"(\d+)/(\d+)\s+(?:processadas|processed|procesadas)", RegexOptions.IgnoreCase | RegexOptions.Compiled);

    public async Task<int> RunAsync(
        CoreOperationRequest request,
        IProgress<CoreProgressEvent> progress,
        CancellationToken cancellationToken)
    {
        var startInfo = CreateStartInfo(request);
        using var process = new Process { StartInfo = startInfo, EnableRaisingEvents = true };
        var outputClosed = new TaskCompletionSource<object?>();
        var errorClosed = new TaskCompletionSource<object?>();

        process.OutputDataReceived += (_, args) =>
        {
            if (args.Data is null)
            {
                outputClosed.TrySetResult(null);
                return;
            }
            progress.Report(ParseLine(args.Data, isError: false));
        };

        process.ErrorDataReceived += (_, args) =>
        {
            if (args.Data is null)
            {
                errorClosed.TrySetResult(null);
                return;
            }
            progress.Report(ParseLine(args.Data, isError: true));
        };

        if (!process.Start())
        {
            throw new InvalidOperationException("The Python core could not be started.");
        }

        process.BeginOutputReadLine();
        process.BeginErrorReadLine();

        using var cancellationRegistration = cancellationToken.Register(() =>
        {
            try
            {
                if (!process.HasExited)
                {
                    process.Kill(entireProcessTree: true);
                }
            }
            catch (InvalidOperationException)
            {
            }
        });

        await process.WaitForExitAsync(cancellationToken);
        await Task.WhenAll(outputClosed.Task, errorClosed.Task);
        return process.ExitCode;
    }

    private static ProcessStartInfo CreateStartInfo(CoreOperationRequest request)
    {
        var coreExe = FindBundledCoreExecutable();
        if (coreExe is not null)
        {
            var bundledStartInfo = new ProcessStartInfo
            {
                FileName = coreExe,
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true,
                StandardOutputEncoding = Encoding.UTF8,
                StandardErrorEncoding = Encoding.UTF8
            };
            ConfigureRealtimeOutput(bundledStartInfo);
            AddArguments(bundledStartInfo, BuildCoreArguments(request));
            return bundledStartInfo;
        }

        var script = FindSourceCoreScript();
        if (script is null)
        {
            throw new FileNotFoundException("photo_organizer.py was not found near the app or repository root.");
        }

        var sourceStartInfo = new ProcessStartInfo
        {
            FileName = FindPythonExecutable(script),
            WorkingDirectory = Path.GetDirectoryName(script) ?? AppContext.BaseDirectory,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true,
            StandardOutputEncoding = Encoding.UTF8,
            StandardErrorEncoding = Encoding.UTF8
        };
        ConfigureRealtimeOutput(sourceStartInfo);
        sourceStartInfo.ArgumentList.Add("-u");
        sourceStartInfo.ArgumentList.Add(script);
        AddArguments(sourceStartInfo, BuildCoreArguments(request));
        return sourceStartInfo;
    }

    private static void ConfigureRealtimeOutput(ProcessStartInfo startInfo)
    {
        startInfo.Environment["PYTHONUNBUFFERED"] = "1";
        startInfo.Environment["PYTHONIOENCODING"] = "utf-8";
    }

    private static IReadOnlyList<string> BuildCoreArguments(CoreOperationRequest request)
    {
        var args = new List<string> { request.SourceFolder, "--language", request.Language };

        if (request.SourceFiles.Count > 0)
        {
            args.Add("--files");
            args.AddRange(request.SourceFiles);
        }

        if (!string.IsNullOrWhiteSpace(request.OutputFolder))
        {
            args.Add("--output-folder");
            args.Add(request.OutputFolder);
        }

        switch (request.Operation)
        {
            case CoreOperation.Organize:
                if (!request.FindDuplicates)
                {
                    args.Add("--skip-duplicates");
                }
                if (request.ApplyChanges)
                {
                    args.Add("--apply");
                }
                if (request.RenameFiles)
                {
                    args.Add("--rename");
                    args.Add("--rename-prefix");
                    args.Add(request.RenamePrefix);
                }
                args.Add("--sensitivity");
                args.Add(request.Sensitivity);
                break;

            case CoreOperation.Convert:
                args.Add("--convert-only");
                if (request.ConvertImages)
                {
                    args.Add("--convert-images");
                }
                if (request.ConvertVideos)
                {
                    args.Add("--convert-videos");
                }
                args.Add("--jpg-quality");
                args.Add(request.JpgQuality.ToString());
                args.Add("--image-format");
                args.Add(request.ImageFormat);
                args.Add("--video-quality");
                args.Add(request.VideoQuality.ToString());
                args.Add("--video-format");
                args.Add(request.VideoFormat);
                break;

            case CoreOperation.Enhance:
                args.Add("--enhance-only");
                args.Add("--enhance-images");
                args.Add("--enhancement-scale");
                args.Add(request.EnhancementScale.ToString());
                args.Add("--enhancement-model");
                args.Add(request.EnhancementModel);
                break;
        }

        return args;
    }

    private static CoreProgressEvent ParseLine(string line, bool isError)
    {
        double? progress = null;
        var percentage = PercentagePattern.Match(line);
        if (percentage.Success && double.TryParse(
                percentage.Groups[1].Value.Replace(',', '.'),
                System.Globalization.NumberStyles.Float,
                System.Globalization.CultureInfo.InvariantCulture,
                out var percent))
        {
            progress = percent;
        }
        else
        {
            var count = CountPattern.Match(line);
            if (count.Success && int.TryParse(count.Groups[1].Value, out var done) &&
                int.TryParse(count.Groups[2].Value, out var total) && total > 0)
            {
                progress = Math.Min(30, 30.0 * done / total);
            }
        }

        return new CoreProgressEvent(line, progress, isError);
    }

    private static string? FindBundledCoreExecutable()
    {
        var baseDirectory = AppContext.BaseDirectory;
        var candidates = new[]
        {
            Path.Combine(baseDirectory, "SimilarisCore.exe"),
            Path.Combine(baseDirectory, "Python", "SimilarisCore.exe")
        };
        return candidates.FirstOrDefault(File.Exists);
    }

    private static string? FindSourceCoreScript()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null)
        {
            var direct = Path.Combine(directory.FullName, "photo_organizer.py");
            if (File.Exists(direct))
            {
                return direct;
            }

            var linked = Path.Combine(directory.FullName, "Python", "photo_organizer.py");
            if (File.Exists(linked))
            {
                return linked;
            }

            directory = directory.Parent;
        }

        return null;
    }

    private static string FindPythonExecutable(string scriptPath)
    {
        var repositoryRoot = new DirectoryInfo(Path.GetDirectoryName(scriptPath)!);
        while (repositoryRoot is not null)
        {
            var venvPython = Path.Combine(repositoryRoot.FullName, ".venv-windows", "Scripts", "python.exe");
            if (File.Exists(venvPython))
            {
                return venvPython;
            }
            repositoryRoot = repositoryRoot.Parent;
        }

        return "python";
    }

    private static void AddArguments(ProcessStartInfo startInfo, IEnumerable<string> arguments)
    {
        foreach (var argument in arguments)
        {
            startInfo.ArgumentList.Add(argument);
        }
    }
}
