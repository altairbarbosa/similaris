namespace Similaris.WinUI.Models;

public enum CoreOperation
{
    Organize,
    Convert,
    Enhance,
    Settings
}

public sealed record CoreOperationRequest(
    CoreOperation Operation,
    string SourceFolder,
    IReadOnlyList<string> SourceFiles,
    string? OutputFolder,
    bool ApplyChanges,
    bool RenameFiles,
    string RenamePrefix,
    bool FindDuplicates,
    bool ConvertImages,
    bool ConvertVideos,
    string ImageFormat,
    string VideoFormat,
    int JpgQuality,
    int VideoQuality,
    int EnhancementScale,
    string EnhancementModel,
    string Sensitivity,
    string Language);

public sealed record CoreProgressEvent(
    string Message,
    double? Progress,
    bool IsError = false);
