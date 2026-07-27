using System.Diagnostics;
using System.Globalization;
using Microsoft.UI;
using Microsoft.UI.Windowing;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Similaris.WinUI.Models;
using Similaris.WinUI.Services;
using Windows.Graphics;
using Windows.ApplicationModel.DataTransfer;
using Windows.Storage.Pickers;
using WinRT.Interop;

namespace Similaris.WinUI;

public sealed partial class MainWindow : Window
{
    private const string SupportUrl =
        "https://www.paypal.com/donate/?business=QUPBFLPKAXG3E&no_recurring=0&item_name=Seu+apoio+ajuda+a+manter+o+projeto+atualizado%2C+corrigir+problemas+e+desenvolver+novos+recursos.&currency_code=BRL";

    private readonly PythonCoreRunner coreRunner = new();
    private AppWindow? appWindow;
    private CancellationTokenSource? runCancellation;
    private CoreOperation currentOperation = CoreOperation.Organize;
    private string currentLanguage = "en-US";
    private readonly List<string> selectedSourceFiles = [];
    private TextBlock? liveLogText;
    private ScrollViewer? liveLogScrollViewer;
    private double estimatedProgress;
    private string? lastCoreError;
    private bool initialized;

    public MainWindow()
    {
        InitializeComponent();
        RootGrid.ActualThemeChanged += (_, _) => ApplyTitleBarTheme();
        RootGrid.SizeChanged += (_, _) => ApplyResponsiveLayout();
        RootGrid.Loaded += (_, _) =>
        {
            ApplyTitleBarTheme();
            DispatcherQueue.TryEnqueue(ApplyResponsiveLayout);
        };
        SetInitialWindowSize();
        AppVersionText.Text = GetAppVersionLabel();
        currentLanguage = DetectLanguage();
        SelectComboByTag(LanguageCombo, currentLanguage);
        SelectComboByTag(ThemeCombo, "system");
        ApplyLanguage();
        LoadLicenses();
        UpdatePage(CoreOperation.Organize);
        UpdateRenamePrefixState();
        UpdateConversionOptionsState();
        initialized = true;
    }

    private void SetInitialWindowSize()
    {
        var windowId = Win32Interop.GetWindowIdFromWindow(WindowNative.GetWindowHandle(this));
        appWindow = AppWindow.GetFromWindowId(windowId);
        var iconPath = Path.Combine(AppContext.BaseDirectory, "Assets", "similaris-icon.ico");
        if (File.Exists(iconPath))
        {
            appWindow.SetIcon(iconPath);
        }

        var workArea = DisplayArea.GetFromWindowId(windowId, DisplayAreaFallback.Primary).WorkArea;
        var width = ScaleToWorkArea(workArea.Width, 0.68, 860, 1220, 0.94);
        var height = ScaleToWorkArea(workArea.Height, 0.88, 720, 940, 0.92);
        appWindow.Resize(new SizeInt32(width, height));
        appWindow.Move(new PointInt32(
            workArea.X + Math.Max(0, (workArea.Width - width) / 2),
            workArea.Y + Math.Max(0, (workArea.Height - height) / 2)));
        ApplyTitleBarTheme();
    }

    private async void ChooseSourceButton_Click(object sender, RoutedEventArgs e)
    {
        if (IsFileSourceMode())
        {
            var files = await PickFilesAsync();
            if (files.Count == 0)
            {
                return;
            }

            selectedSourceFiles.Clear();
            selectedSourceFiles.AddRange(files);
            SourcePathBox.Text = files.Count == 1
                ? files[0]
                : string.Format(T("source_files_selected"), files.Count);
            ShowStatus(T("status_ready"), T("source_files_selected_status"), InfoBarSeverity.Success);
            return;
        }

        var folder = await PickFolderAsync();
        if (!string.IsNullOrWhiteSpace(folder))
        {
            selectedSourceFiles.Clear();
            SourcePathBox.Text = folder;
            ShowStatus(T("status_ready"), T("source_selected"), InfoBarSeverity.Success);
        }
    }

    private void SourceModeRadio_Checked(object sender, RoutedEventArgs e)
    {
        if (!initialized)
        {
            return;
        }

        selectedSourceFiles.Clear();
        SourcePathBox.Text = string.Empty;
        SourcePathBox.PlaceholderText = IsFileSourceMode() ? T("source_files_placeholder") : T("source_placeholder");
        SourceDescriptionText.Text = IsFileSourceMode() ? T("source_files_description") : T("source_description");
        ChooseSourceButton.Content = IsFileSourceMode() ? T("choose_files") : T("choose");
    }

    private async void ChooseOutputButton_Click(object sender, RoutedEventArgs e)
    {
        var folder = await PickFolderAsync();
        if (!string.IsNullOrWhiteSpace(folder))
        {
            OutputPathBox.Text = folder;
        }
    }

    private void ClearOutputButton_Click(object sender, RoutedEventArgs e)
    {
        OutputPathBox.Text = string.Empty;
    }

    private void RenameFilesCheck_Changed(object sender, RoutedEventArgs e)
    {
        UpdateRenamePrefixState();
    }

    private void ConvertTypeOptions_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        UpdateConversionOptionsState();
    }

    private async void StartButton_Click(object sender, RoutedEventArgs e)
    {
        if (string.IsNullOrWhiteSpace(SourcePathBox.Text))
        {
            ShowStatus(T("source_required"), T("source_required_message"), InfoBarSeverity.Warning);
            return;
        }

        runCancellation = new CancellationTokenSource();
        SetRunningState(true);
        LogBox.Text = string.Empty;
        if (liveLogText is not null)
        {
            liveLogText.Text = string.Empty;
        }
        estimatedProgress = 0;
        lastCoreError = null;
        OperationProgress.Value = 0;
        OperationProgress.IsIndeterminate = false;
        ProgressPercentText.Text = "0%";
        CurrentStepText.Text = T("starting");
        ShowStatus(T("running"), T("running_message"), InfoBarSeverity.Informational);

        var request = BuildRequest();
        var stopwatch = Stopwatch.StartNew();
        var progress = new Progress<CoreProgressEvent>(OnCoreProgress);

        try
        {
            var exitCode = await coreRunner.RunAsync(request, progress, runCancellation.Token);
            stopwatch.Stop();
            if (exitCode == 0)
            {
                OperationProgress.IsIndeterminate = false;
                OperationProgress.Value = 100;
                ProgressPercentText.Text = "100%";
                CurrentStepText.Text = T("completed");
                ShowStatus(T("completed"), string.Format(T("completed_message"), stopwatch.Elapsed), InfoBarSeverity.Success);
            }
            else
            {
                OperationProgress.IsIndeterminate = false;
                ProgressPercentText.Text = T("progress_error");
                CurrentStepText.Text = T("completed_errors");
                var errorMessage = string.IsNullOrWhiteSpace(lastCoreError)
                    ? string.Format(T("exit_code_message"), exitCode)
                    : lastCoreError;
                ShowStatus(T("completed_errors"), errorMessage, InfoBarSeverity.Error);
            }
        }
        catch (OperationCanceledException)
        {
            OperationProgress.IsIndeterminate = false;
            ProgressPercentText.Text = T("progress_canceled");
            CurrentStepText.Text = T("canceled");
            ShowStatus(T("canceled"), T("canceled_message"), InfoBarSeverity.Warning);
        }
        catch (Exception ex)
        {
            OperationProgress.IsIndeterminate = false;
            ProgressPercentText.Text = T("progress_error");
            CurrentStepText.Text = T("could_not_start");
            AppendLog(ex.ToString(), isError: true);
            ShowStatus(T("could_not_start"), ex.Message, InfoBarSeverity.Error);
        }
        finally
        {
            SetRunningState(false);
            runCancellation?.Dispose();
            runCancellation = null;
        }
    }

    private void CancelButton_Click(object sender, RoutedEventArgs e)
    {
        runCancellation?.Cancel();
    }

    private void RootNavigation_SelectionChanged(NavigationView sender, NavigationViewSelectionChangedEventArgs args)
    {
        if (args.SelectedItemContainer?.Tag is not string tag)
        {
            return;
        }

        currentOperation = tag switch
        {
            "convert" => CoreOperation.Convert,
            "enhance" => CoreOperation.Enhance,
            "settings" => CoreOperation.Settings,
            _ => CoreOperation.Organize
        };
        UpdatePage(currentOperation);
    }

    private void LanguageCombo_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (!initialized || LanguageCombo.SelectedItem is not ComboBoxItem item)
        {
            return;
        }

        currentLanguage = item.Tag?.ToString() ?? "en-US";
        ApplyLanguage();
        UpdatePage(currentOperation);
        ShowStatus(T("status_ready"), T("language_updated"), InfoBarSeverity.Success);
    }

    private void ThemeCombo_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (!initialized || ThemeCombo.SelectedItem is not ComboBoxItem item)
        {
            return;
        }

        RootGrid.RequestedTheme = (item.Tag?.ToString()) switch
        {
            "light" => ElementTheme.Light,
            "dark" => ElementTheme.Dark,
            _ => ElementTheme.Default
        };
        ApplyTitleBarTheme();
    }

    private void ApplyTitleBarTheme()
    {
        if (appWindow is null || !AppWindowTitleBar.IsCustomizationSupported())
        {
            return;
        }

        var titleBar = appWindow.TitleBar;
        var isDark = RootGrid.ActualTheme == ElementTheme.Dark;
        var background = isDark ? ColorHelper.FromArgb(255, 32, 32, 32) : ColorHelper.FromArgb(255, 243, 243, 243);
        var foreground = isDark ? Colors.White : Colors.Black;
        var inactiveBackground = background;
        var hoverBackground = isDark ? ColorHelper.FromArgb(255, 44, 44, 44) : ColorHelper.FromArgb(255, 232, 232, 232);
        var pressedBackground = isDark ? ColorHelper.FromArgb(255, 56, 56, 56) : ColorHelper.FromArgb(255, 216, 216, 216);

        titleBar.BackgroundColor = background;
        titleBar.ForegroundColor = foreground;
        titleBar.InactiveBackgroundColor = inactiveBackground;
        titleBar.InactiveForegroundColor = foreground;
        titleBar.ButtonBackgroundColor = background;
        titleBar.ButtonForegroundColor = foreground;
        titleBar.ButtonInactiveBackgroundColor = inactiveBackground;
        titleBar.ButtonInactiveForegroundColor = foreground;
        titleBar.ButtonHoverBackgroundColor = hoverBackground;
        titleBar.ButtonHoverForegroundColor = foreground;
        titleBar.ButtonPressedBackgroundColor = pressedBackground;
        titleBar.ButtonPressedForegroundColor = foreground;
    }

    private static int ScaleToWorkArea(int workAreaSize, double preferredRatio, int minSize, int maxSize, double maxRatio)
    {
        var preferred = (int)Math.Round(workAreaSize * preferredRatio);
        var upperBound = Math.Min(maxSize, (int)Math.Round(workAreaSize * maxRatio));
        var lowerBound = Math.Min(minSize, upperBound);
        return Math.Clamp(preferred, lowerBound, upperBound);
    }

    private void SettingsSelector_SelectionChanged(SelectorBar sender, SelectorBarSelectionChangedEventArgs args)
    {
        var selected = sender.SelectedItem;
        AppearanceSettingsPanel.Visibility = selected == AppearanceSelectorItem ? Visibility.Visible : Visibility.Collapsed;
        SupportSettingsPanel.Visibility = selected == SupportSelectorItem ? Visibility.Visible : Visibility.Collapsed;
        LicensesSettingsPanel.Visibility = selected == LicensesSelectorItem ? Visibility.Visible : Visibility.Collapsed;
    }

    private void MainScrollViewer_SizeChanged(object sender, SizeChangedEventArgs e)
    {
        ApplyResponsiveLayout();
    }

    private void ApplyResponsiveLayout()
    {
        var viewportWidth = MainScrollViewer.ViewportWidth > 0 ? MainScrollViewer.ViewportWidth : RootGrid.ActualWidth;
        var shouldStackSidePanel = viewportWidth < 1120;
        var shouldUseWideCards = viewportWidth >= 1480;
        var contentMaxWidth = shouldStackSidePanel ? 920 : 1600;
        var contentWidth = Math.Max(0, Math.Min(viewportWidth, contentMaxWidth));

        MainContentGrid.ColumnDefinitions[1].Width = shouldStackSidePanel
            ? new GridLength(0)
            : new GridLength(360);
        MainContentGrid.ColumnSpacing = shouldStackSidePanel ? 0 : 24;
        MainContentGrid.RowSpacing = shouldStackSidePanel ? 20 : 0;
        MainContentGrid.Width = contentWidth;
        MainContentGrid.MaxWidth = contentMaxWidth;

        Grid.SetColumn(SidePanel, shouldStackSidePanel ? 0 : 1);
        Grid.SetRow(SidePanel, shouldStackSidePanel ? 1 : 0);
        Grid.SetColumnSpan(SidePanel, 1);

        OperationContent.ColumnDefinitions[1].Width = shouldUseWideCards
            ? new GridLength(1, GridUnitType.Star)
            : new GridLength(0);
        OperationContent.ColumnSpacing = shouldUseWideCards ? 16 : 0;

        Grid.SetRow(SourceCard, 0);
        Grid.SetColumn(SourceCard, 0);
        Grid.SetColumnSpan(SourceCard, shouldUseWideCards ? 1 : 2);

        Grid.SetRow(DestinationCard, shouldUseWideCards ? 0 : 1);
        Grid.SetColumn(DestinationCard, shouldUseWideCards ? 1 : 0);
        Grid.SetColumnSpan(DestinationCard, shouldUseWideCards ? 1 : 2);

        var operationRow = shouldUseWideCards ? 1 : 2;
        foreach (var page in new[] { OrganizePage, ConvertPage, EnhancePage })
        {
            Grid.SetRow(page, operationRow);
            Grid.SetColumn(page, 0);
            Grid.SetColumnSpan(page, 2);
        }
    }

    private async void ViewLogButton_Click(object sender, RoutedEventArgs e)
    {
        var textBlock = new TextBlock
        {
            Text = string.IsNullOrWhiteSpace(LogBox.Text) ? T("log_placeholder") : LogBox.Text,
            TextWrapping = TextWrapping.Wrap,
            FontFamily = new Microsoft.UI.Xaml.Media.FontFamily("Consolas"),
            FontSize = 12,
            Padding = new Thickness(12)
        };
        var scrollViewer = new ScrollViewer
        {
            Width = 680,
            MaxWidth = 760,
            Height = 440,
            MaxHeight = 520,
            HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled,
            VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
            Content = textBlock
        };
        liveLogText = textBlock;
        liveLogScrollViewer = scrollViewer;
        ScrollLiveLogToEnd();

        var dialog = new ContentDialog
        {
            XamlRoot = RootGrid.XamlRoot,
            Title = T("processing_log"),
            PrimaryButtonText = T("copy"),
            CloseButtonText = T("close"),
            DefaultButton = ContentDialogButton.Close,
            Content = scrollViewer
        };

        var result = await dialog.ShowAsync();
        if (ReferenceEquals(liveLogText, textBlock))
        {
            liveLogText = null;
            liveLogScrollViewer = null;
        }
        if (result == ContentDialogResult.Primary)
        {
            CopyLogToClipboard();
        }
    }

    private void DonateButton_Click(object sender, RoutedEventArgs e)
    {
        Process.Start(new ProcessStartInfo
        {
            FileName = SupportUrl,
            UseShellExecute = true
        });
    }

    private CoreOperationRequest BuildRequest()
    {
        return new CoreOperationRequest(
            currentOperation,
            GetSourceFolderForRequest(),
            selectedSourceFiles.ToArray(),
            string.IsNullOrWhiteSpace(OutputPathBox.Text) ? null : OutputPathBox.Text,
            currentOperation == CoreOperation.Organize,
            RenameFilesCheck.IsChecked == true,
            string.IsNullOrWhiteSpace(RenamePrefixBox.Text) ? "img" : RenamePrefixBox.Text.Trim(),
            true,
            IsImageConversionMode(),
            !IsImageConversionMode(),
            GetSelectedTag(ImageFormatCombo),
            GetSelectedTag(VideoFormatCombo),
            (int)Math.Round(JpgQualitySlider.Value),
            GetVideoCrfFromQuality(),
            int.Parse(GetSelectedTag(EnhancementScaleCombo)),
            GetSelectedTag(EnhancementModelCombo),
            GetSelectedSensitivity(),
            currentLanguage);
    }

    private async Task<string?> PickFolderAsync()
    {
        var picker = new FolderPicker();
        InitializeWithWindow.Initialize(picker, WindowNative.GetWindowHandle(this));
        picker.FileTypeFilter.Add("*");
        var folder = await picker.PickSingleFolderAsync();
        return folder?.Path;
    }

    private async Task<IReadOnlyList<string>> PickFilesAsync()
    {
        var picker = new FileOpenPicker();
        InitializeWithWindow.Initialize(picker, WindowNative.GetWindowHandle(this));
        foreach (var extension in new[]
                 { ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".mp4", ".mov", ".avi", ".mkv", ".webm" })
        {
            picker.FileTypeFilter.Add(extension);
        }
        var files = await picker.PickMultipleFilesAsync();
        return files.Select(file => file.Path).Where(path => !string.IsNullOrWhiteSpace(path)).ToArray();
    }

    private bool IsFileSourceMode()
    {
        return SourceModeFilesRadio.IsChecked == true;
    }

    private string GetSourceFolderForRequest()
    {
        if (selectedSourceFiles.Count == 0)
        {
            return SourcePathBox.Text;
        }

        return Path.GetDirectoryName(selectedSourceFiles[0]) ?? Environment.CurrentDirectory;
    }

    private void UpdatePage(CoreOperation operation)
    {
        OperationContent.Visibility = operation == CoreOperation.Settings ? Visibility.Collapsed : Visibility.Visible;
        SettingsPage.Visibility = operation == CoreOperation.Settings ? Visibility.Visible : Visibility.Collapsed;
        SidePanel.Visibility = operation == CoreOperation.Settings ? Visibility.Collapsed : Visibility.Visible;
        ActionButtonsPanel.Visibility = operation == CoreOperation.Settings ? Visibility.Collapsed : Visibility.Visible;

        OrganizePage.Visibility = operation == CoreOperation.Organize ? Visibility.Visible : Visibility.Collapsed;
        ConvertPage.Visibility = operation == CoreOperation.Convert ? Visibility.Visible : Visibility.Collapsed;
        EnhancePage.Visibility = operation == CoreOperation.Enhance ? Visibility.Visible : Visibility.Collapsed;

        switch (operation)
        {
            case CoreOperation.Convert:
                PageTitleText.Text = T("convert_title");
                PageDescriptionText.Text = T("convert_description");
                StartButton.Content = T("start_convert");
                break;
            case CoreOperation.Enhance:
                PageTitleText.Text = T("enhance_title");
                PageDescriptionText.Text = T("enhance_description");
                StartButton.Content = T("start_enhance");
                break;
            case CoreOperation.Settings:
                PageTitleText.Text = T("settings_title");
                PageDescriptionText.Text = T("settings_description");
                break;
            default:
                PageTitleText.Text = T("organize_title");
                PageDescriptionText.Text = T("organize_description");
                StartButton.Content = T("start_organize");
                break;
        }

        DispatcherQueue.TryEnqueue(ApplyResponsiveLayout);
    }

    private void SetRunningState(bool running)
    {
        StartButton.IsEnabled = !running;
        CancelButton.IsEnabled = running;
    }

    private void UpdateRenamePrefixState()
    {
        RenamePrefixPanel.Visibility = RenameFilesCheck.IsChecked == true
            ? Visibility.Visible
            : Visibility.Collapsed;
    }

    private void UpdateConversionOptionsState()
    {
        var imageMode = IsImageConversionMode();
        ImageConversionPanel.Visibility = imageMode ? Visibility.Visible : Visibility.Collapsed;
        VideoConversionPanel.Visibility = imageMode ? Visibility.Collapsed : Visibility.Visible;
    }

    private bool IsImageConversionMode()
    {
        return (ConvertTypeOptions.SelectedItem as RadioButton)?.Tag?.ToString() != "videos";
    }

    private void OnCoreProgress(CoreProgressEvent progress)
    {
        if (progress.IsError)
        {
            lastCoreError = progress.Message;
        }
        AppendLog(progress.Message, progress.IsError);
        CurrentStepText.Text = DescribeProgressMessage(progress.Message, progress.IsError);
        if (progress.Progress is { } value)
        {
            var bounded = Math.Clamp(value, 0, 100);
            estimatedProgress = Math.Max(estimatedProgress, bounded);
            OperationProgress.IsIndeterminate = false;
            OperationProgress.Value = estimatedProgress;
            ProgressPercentText.Text = string.Format(CultureInfo.InvariantCulture, "{0:0}%", estimatedProgress);
        }
        else
        {
            UpdateEstimatedProgress(progress.Message);
        }
    }

    private void AppendLog(string message, bool isError)
    {
        var prefix = isError ? "[error] " : string.Empty;
        var line = prefix + message;
        LogBox.Text += line + Environment.NewLine;
        if (liveLogText is not null)
        {
            liveLogText.Text += line + Environment.NewLine;
            ScrollLiveLogToEnd();
        }
    }

    private void ScrollLiveLogToEnd()
    {
        if (liveLogScrollViewer is null)
        {
            return;
        }

        liveLogScrollViewer.UpdateLayout();
        liveLogScrollViewer.ChangeView(null, liveLogScrollViewer.ScrollableHeight, null, disableAnimation: true);
    }

    private void UpdateEstimatedProgress(string message)
    {
        var text = message.ToLowerInvariant();
        var floor = text switch
        {
            var value when value.Contains("convertendo") || value.Contains("converting") || value.Contains("convirtiendo") => 18,
            var value when value.Contains("analisando") || value.Contains("analyzing") || value.Contains("analizando") => 10,
            var value when value.Contains("comparando") || value.Contains("comparing") => 38,
            var value when value.Contains("real-esrgan") || value.Contains("melhoria") || value.Contains("enhance") || value.Contains("mejora") => 20,
            var value when value.Contains("validando") || value.Contains("validating") => 76,
            var value when value.Contains("relat") || value.Contains("report") || value.Contains("salvo") || value.Contains("saved") || value.Contains("guardado") => 88,
            var value when value.Contains("conclu") || value.Contains("completed") || value.Contains("finished") || value.Contains("finalizado") => 96,
            _ => 5
        };

        estimatedProgress = Math.Min(96, Math.Max(Math.Max(estimatedProgress + 2, floor), OperationProgress.Value));
        OperationProgress.IsIndeterminate = false;
        OperationProgress.Value = estimatedProgress;
        ProgressPercentText.Text = string.Format(CultureInfo.InvariantCulture, "{0:0}%", estimatedProgress);
    }

    private void CopyLogToClipboard()
    {
        var package = new DataPackage();
        package.SetText(LogBox.Text);
        Clipboard.SetContent(package);
    }

    private string DescribeProgressMessage(string message, bool isError)
    {
        if (isError)
        {
            return T("step_error");
        }

        var text = message.ToLowerInvariant();
        if (text.Contains("comparando") || text.Contains("comparing") || text.Contains("comparando"))
        {
            return T("step_comparing");
        }
        if (text.Contains("analisando") || text.Contains("analyzing") || text.Contains("analizando"))
        {
            return T("step_analyzing");
        }
        if (text.Contains("convertendo") || text.Contains("converting") || text.Contains("convirtiendo"))
        {
            return T("step_converting");
        }
        if (text.Contains("enhance") || text.Contains("real-esrgan") || text.Contains("melhoria") || text.Contains("mejora"))
        {
            return T("step_enhancing");
        }
        if (text.Contains("validando") || text.Contains("validating"))
        {
            return T("step_validating");
        }
        if (text.Contains("relatório") || text.Contains("report") || text.Contains("archivo guardado") || text.Contains("arquivo salvo"))
        {
            return T("step_saving");
        }
        if (text.Contains("conclu") || text.Contains("completed") || text.Contains("finished") || text.Contains("finalizado"))
        {
            return T("step_finished");
        }

        return T("step_processing");
    }

    private void ShowStatus(string title, string message, InfoBarSeverity severity)
    {
        StatusTitleText.Text = title;
        StatusMessageText.Text = message;
        StatusIcon.Glyph = severity switch
        {
            InfoBarSeverity.Success => "\uE73E",
            InfoBarSeverity.Warning => "\uE7BA",
            InfoBarSeverity.Error => "\uEA39",
            _ => "\uE946"
        };
    }

    private void ApplyLanguage()
    {
        OrganizeNavItem.Content = T("nav_organize");
        ConvertNavItem.Content = T("nav_convert");
        EnhanceNavItem.Content = T("nav_enhance");
        SettingsNavItem.Content = T("nav_settings");
        CancelButton.Content = T("cancel");
        ChooseSourceButton.Content = T("choose");
        ChooseOutputButton.Content = T("choose");
        ClearOutputButton.Content = T("clear");
        ToolTipService.SetToolTip(ViewLogButton, T("view_log"));
        DonateButton.Content = T("donate");
        ProgressTitleText.Text = T("progress");

        SourceTitleText.Text = T("source");
        SourceDescriptionText.Text = IsFileSourceMode() ? T("source_files_description") : T("source_description");
        SourcePathBox.PlaceholderText = IsFileSourceMode() ? T("source_files_placeholder") : T("source_placeholder");
        SourceModeFolderRadio.Content = T("source_mode_folder");
        SourceModeFilesRadio.Content = T("source_mode_files");
        ChooseSourceButton.Content = IsFileSourceMode() ? T("choose_files") : T("choose");
        DestinationTitleText.Text = T("destination");
        DestinationDescriptionText.Text = T("destination_description");
        OutputPathBox.PlaceholderText = T("destination_placeholder");

        OrganizeSectionTitleText.Text = T("organize_section_title");
        OrganizeSectionDescriptionText.Text = T("organize_section_description");
        RenameFilesCheck.Content = T("rename_files");
        RenamePrefixBox.Header = T("rename_prefix");
        RenameExampleText.Text = T("rename_example");
        SensitivityLabelText.Text = T("sensitivity");
        SensitivitySaferText.Text = T("sensitivity_safer");
        SensitivityBalancedText.Text = T("sensitivity_balanced");
        SensitivityBroaderText.Text = T("sensitivity_broader");
        SensitivitySaferDescriptionText.Text = T("sensitivity_safer_description");
        SensitivityBalancedDescriptionText.Text = T("sensitivity_balanced_description");
        SensitivityBroaderDescriptionText.Text = T("sensitivity_broader_description");

        ConvertSectionTitleText.Text = T("convert_section_title");
        ConvertSectionDescriptionText.Text = T("convert_section_description");
        ConvertTypeLabelText.Text = T("conversion_type");
        ConvertImagesOption.Content = T("convert_images");
        ConvertVideosOption.Content = T("convert_videos");
        ImageFormatCombo.Header = T("image_format");
        VideoFormatCombo.Header = T("video_format");
        JpgQualityText.Text = T("jpg_quality");
        VideoQualityText.Text = T("video_quality");

        EnhanceSectionTitleText.Text = T("enhance_section_title");
        EnhanceSectionDescriptionText.Text = T("enhance_section_description");
        EnhancementScaleCombo.Header = T("upscale");
        EnhancementModelCombo.Header = T("image_type");
        EnhancementPhotoItem.Content = T("photo");
        EnhancementIllustrationItem.Content = T("illustration");

        AppearanceTitleText.Text = T("appearance_title");
        BrandDescriptionText.Text = T("brand_description");
        AppearanceDescriptionText.Text = T("appearance_description");
        LanguageCombo.Header = T("language");
        ThemeCombo.Header = T("theme");
        ThemeSystemItem.Content = T("theme_system");
        ThemeLightItem.Content = T("theme_light");
        ThemeDarkItem.Content = T("theme_dark");
        SupportTitleText.Text = T("support_title");
        AppearanceSelectorItem.Text = T("appearance_tab");
        SupportSelectorItem.Text = T("support_tab");
        LicensesSelectorItem.Text = T("licenses_tab");
        SupportDescriptionText.Text = T("support_description");
        LicensesTitleText.Text = T("licenses_title");
        LicensesDescriptionText.Text = T("licenses_description");

        LogBox.PlaceholderText = T("log_placeholder");
        if (!OperationProgress.IsIndeterminate && OperationProgress.Value <= 0)
        {
            ProgressPercentText.Text = "0%";
            CurrentStepText.Text = T("waiting_to_start");
        }
        ShowStatus(T("status_ready"), T("ready_message"), InfoBarSeverity.Informational);
    }

    private void LoadLicenses()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null)
        {
            var candidates = new[]
            {
                Path.Combine(directory.FullName, "Licenses", "THIRD_PARTY_NOTICES.txt"),
                Path.Combine(directory.FullName, "THIRD_PARTY_NOTICES.txt")
            };
            var path = candidates.FirstOrDefault(File.Exists);
            if (path is not null)
            {
                LicensesBox.Text = File.ReadAllText(path);
                return;
            }
            directory = directory.Parent;
        }

        LicensesBox.Text = T("licenses_missing");
    }

    private string T(string key)
    {
        return Strings[currentLanguage].TryGetValue(key, out var value)
            ? value
            : Strings["en-US"][key];
    }

    private static string DetectLanguage()
    {
        var language = CultureInfo.CurrentUICulture.Name.ToLowerInvariant();
        if (language.StartsWith("pt"))
        {
            return "pt-BR";
        }
        if (language.StartsWith("es"))
        {
            return "es-ES";
        }
        return "en-US";
    }

    private static string GetAppVersionLabel()
    {
        var version = typeof(MainWindow).Assembly.GetName().Version;
        return version is null
            ? "v0.0.0.0"
            : string.Format(CultureInfo.InvariantCulture, "v{0}.{1}.{2}.{3}", version.Major, version.Minor, version.Build, version.Revision);
    }

    private static string GetSelectedTag(ComboBox comboBox)
    {
        return ((ComboBoxItem)comboBox.SelectedItem).Tag?.ToString() ?? string.Empty;
    }

    private string GetSelectedSensitivity()
    {
        return (SensitivityOptions.SelectedItem as RadioButton)?.Tag?.ToString() ?? "balanced";
    }

    private int GetVideoCrfFromQuality()
    {
        var quality = Math.Clamp(VideoQualitySlider.Value, 1, 100);
        return (int)Math.Round(35 - ((quality - 1) * 17 / 99));
    }

    private static void SelectComboByTag(ComboBox comboBox, string tag)
    {
        foreach (var item in comboBox.Items.OfType<ComboBoxItem>())
        {
            if (item.Tag?.ToString() == tag)
            {
                comboBox.SelectedItem = item;
                return;
            }
        }
    }

    private static readonly Dictionary<string, Dictionary<string, string>> Strings = new()
    {
        ["en-US"] = new()
        {
            ["nav_organize"] = "Organize", ["nav_convert"] = "Convert", ["nav_enhance"] = "Enhance", ["nav_settings"] = "Settings",
            ["pane_subtitle"] = "Python-powered media tools", ["brand_description"] = "Find duplicate images, convert media, and enhance images locally.",
            ["organize_title"] = "Organize images", ["organize_description"] = "Find visual duplicates and standardize file names with the Python core.",
            ["convert_title"] = "Convert files", ["convert_description"] = "Convert images and videos through the Python core while preserving originals.",
            ["enhance_title"] = "Enhance images", ["enhance_description"] = "Run local Real-ESRGAN enhancement without moving your originals.",
            ["settings_title"] = "Settings", ["settings_description"] = "Personalize Similaris, review licenses, and support development.",
            ["cancel"] = "Cancel", ["choose"] = "Choose...", ["choose_files"] = "Choose files...", ["clear"] = "Clear", ["copy"] = "Copy", ["view"] = "View", ["close"] = "Close", ["donate"] = "Make a donation",
            ["source"] = "Source", ["source_description"] = "Choose the folder the Python core will process.", ["source_files_description"] = "Choose specific files the Python core will process.",
            ["source_placeholder"] = "No source selected", ["source_files_placeholder"] = "No files selected", ["source_mode_folder"] = "Folder", ["source_mode_files"] = "Files",
            ["source_files_selected"] = "{0} files selected", ["source_files_selected_status"] = "Source files selected.",
            ["destination"] = "Destination", ["destination_description"] = "Leave empty to use the operation's default output folder.", ["destination_placeholder"] = "Default destination",
            ["organize_section_title"] = "Image organization", ["organize_section_description"] = "Separate duplicate images and optionally standardize file names.",
            ["rename_files"] = "Standardize file names", ["rename_prefix"] = "Prefix", ["rename_example"] = "Example: img (1).jpg",
            ["sensitivity"] = "Sensitivity", ["sensitivity_safer"] = "Safer", ["sensitivity_balanced"] = "Balanced", ["sensitivity_broader"] = "Broader",
            ["sensitivity_safer_description"] = "More strict.", ["sensitivity_balanced_description"] = "Recommended.", ["sensitivity_broader_description"] = "More matches.",
            ["convert_section_title"] = "File conversion", ["convert_section_description"] = "Choose one media type and create converted copies while preserving originals.",
            ["conversion_type"] = "Conversion type", ["convert_images"] = "Images", ["convert_videos"] = "Videos", ["image_format"] = "Image format", ["video_format"] = "Video format", ["jpg_quality"] = "Image quality", ["video_quality"] = "Video quality",
            ["enhance_section_title"] = "Image enhancement", ["enhance_section_description"] = "Run Real-ESRGAN locally through the Python core.",
            ["upscale"] = "Upscale", ["image_type"] = "Image type", ["photo"] = "Photo", ["illustration"] = "Illustration",
            ["appearance_title"] = "Appearance and language", ["appearance_description"] = "Personalize Similaris and choose the language used by the Python core.",
            ["appearance_tab"] = "Appearance", ["support_tab"] = "Support", ["licenses_tab"] = "Licenses",
            ["language"] = "Language", ["theme"] = "Theme", ["theme_system"] = "System", ["theme_light"] = "Light", ["theme_dark"] = "Dark",
            ["support_title"] = "Support Similaris development", ["support_description"] = "Similaris is free and independently developed. Contributions help keep the project updated.",
            ["licenses_title"] = "Licenses", ["licenses_description"] = "Review the licenses bundled with Similaris and third-party components.", ["licenses_missing"] = "License notices were not found.",
            ["processing_log"] = "Processing log", ["log_placeholder"] = "Core output will appear here.", ["open_destination"] = "Open destination",
            ["core_idle"] = "Python core idle", ["core_running"] = "Python core running",
            ["progress"] = "Progress", ["progress_pending"] = "Calculating...", ["progress_error"] = "Error", ["progress_canceled"] = "Canceled",
            ["waiting_to_start"] = "Waiting to start.", ["starting"] = "Starting Python core...",
            ["view_log"] = "View execution log", ["step_processing"] = "Processing files", ["step_analyzing"] = "Analyzing files",
            ["step_comparing"] = "Comparing visual similarity", ["step_converting"] = "Converting media", ["step_enhancing"] = "Enhancing images",
            ["step_validating"] = "Validating results", ["step_saving"] = "Saving outputs", ["step_finished"] = "Finishing operation", ["step_error"] = "Reviewing an error",
            ["status_ready"] = "Ready", ["ready_message"] = "Select a source folder to begin.", ["source_selected"] = "Source folder selected.", ["language_updated"] = "Language updated.",
            ["source_required"] = "Source required", ["source_required_message"] = "Choose a source folder before starting.",
            ["running"] = "Running", ["running_message"] = "The Python core is processing your files.", ["completed"] = "Completed", ["completed_message"] = "Finished in {0:mm\\:ss}.",
            ["completed_errors"] = "Completed with errors", ["exit_code_message"] = "The Python core exited with code {0}.", ["canceled"] = "Canceled", ["canceled_message"] = "The operation was canceled.",
            ["could_not_start"] = "Could not start", ["destination_unavailable"] = "Destination unavailable", ["destination_unavailable_message"] = "Choose an existing destination folder first.",
            ["start_organize"] = "Organize", ["start_convert"] = "Convert", ["start_enhance"] = "Enhance"
        },
        ["pt-BR"] = new()
        {
            ["nav_organize"] = "Organizar", ["nav_convert"] = "Converter", ["nav_enhance"] = "Aprimorar", ["nav_settings"] = "Configurações",
            ["pane_subtitle"] = "Ferramentas de mídia com Python", ["brand_description"] = "Encontre imagens duplicadas, converta mídia e melhore imagens localmente.",
            ["organize_title"] = "Organizar imagens", ["organize_description"] = "Encontre duplicatas visuais e padronize nomes com o core Python.",
            ["convert_title"] = "Converter arquivos", ["convert_description"] = "Converta imagens e vídeos pelo core Python preservando os originais.",
            ["enhance_title"] = "Aprimorar imagens", ["enhance_description"] = "Execute melhoria local com Real-ESRGAN sem mover os originais.",
            ["settings_title"] = "Configurações", ["settings_description"] = "Personalize o Similaris, consulte licenças e apoie o desenvolvimento.",
            ["cancel"] = "Cancelar", ["choose"] = "Escolher...", ["choose_files"] = "Escolher arquivos...", ["clear"] = "Limpar", ["copy"] = "Copiar", ["view"] = "Ver", ["close"] = "Fechar", ["donate"] = "Fazer uma doação",
            ["source"] = "Origem", ["source_description"] = "Escolha a pasta que o core Python irá processar.", ["source_files_description"] = "Escolha arquivos específicos que o core Python irá processar.",
            ["source_placeholder"] = "Nenhuma origem selecionada", ["source_files_placeholder"] = "Nenhum arquivo selecionado", ["source_mode_folder"] = "Pasta", ["source_mode_files"] = "Arquivos",
            ["source_files_selected"] = "{0} arquivos selecionados", ["source_files_selected_status"] = "Arquivos de origem selecionados.",
            ["destination"] = "Destino", ["destination_description"] = "Deixe vazio para usar o destino padrão da operação.", ["destination_placeholder"] = "Destino padrão",
            ["organize_section_title"] = "Organização de imagens", ["organize_section_description"] = "Separe imagens duplicadas e, se quiser, padronize os nomes dos arquivos.",
            ["rename_files"] = "Padronizar nomes dos arquivos", ["rename_prefix"] = "Prefixo", ["rename_example"] = "Exemplo: img (1).jpg",
            ["sensitivity"] = "Sensibilidade", ["sensitivity_safer"] = "Mais segura", ["sensitivity_balanced"] = "Equilibrada", ["sensitivity_broader"] = "Mais abrangente",
            ["sensitivity_safer_description"] = "Mais rigorosa.", ["sensitivity_balanced_description"] = "Recomendada.", ["sensitivity_broader_description"] = "Mais achados.",
            ["convert_section_title"] = "Conversão de arquivos", ["convert_section_description"] = "Escolha um tipo de mídia e crie cópias convertidas preservando os originais.",
            ["conversion_type"] = "Tipo de conversão", ["convert_images"] = "Imagens", ["convert_videos"] = "Vídeos", ["image_format"] = "Formato da imagem", ["video_format"] = "Formato do vídeo", ["jpg_quality"] = "Qualidade da imagem", ["video_quality"] = "Qualidade do vídeo",
            ["enhance_section_title"] = "Melhoria de imagens", ["enhance_section_description"] = "Execute o Real-ESRGAN localmente pelo core Python.",
            ["upscale"] = "Ampliação", ["image_type"] = "Tipo de imagem", ["photo"] = "Foto", ["illustration"] = "Ilustração",
            ["appearance_title"] = "Aparência e idioma", ["appearance_description"] = "Personalize o Similaris e escolha o idioma usado pelo core Python.",
            ["appearance_tab"] = "Aparência", ["support_tab"] = "Apoie", ["licenses_tab"] = "Licenças",
            ["language"] = "Idioma", ["theme"] = "Tema", ["theme_system"] = "Sistema", ["theme_light"] = "Claro", ["theme_dark"] = "Escuro",
            ["support_title"] = "Apoie o desenvolvimento do Similaris", ["support_description"] = "O Similaris é gratuito e desenvolvido de forma independente. Contribuições ajudam a manter o projeto atualizado.",
            ["licenses_title"] = "Licenças", ["licenses_description"] = "Consulte as licenças incluídas com o Similaris e componentes de terceiros.", ["licenses_missing"] = "Os avisos de licença não foram encontrados.",
            ["processing_log"] = "Log de processamento", ["log_placeholder"] = "A saída do core aparecerá aqui.", ["open_destination"] = "Abrir destino",
            ["core_idle"] = "Core Python inativo", ["core_running"] = "Core Python em execução",
            ["progress"] = "Progresso", ["progress_pending"] = "Calculando...", ["progress_error"] = "Erro", ["progress_canceled"] = "Cancelado",
            ["waiting_to_start"] = "Aguardando início.", ["starting"] = "Iniciando o core Python...",
            ["view_log"] = "Ver log de execução", ["step_processing"] = "Processando arquivos", ["step_analyzing"] = "Analisando arquivos",
            ["step_comparing"] = "Comparando similaridade visual", ["step_converting"] = "Convertendo mídia", ["step_enhancing"] = "Aprimorando imagens",
            ["step_validating"] = "Validando resultados", ["step_saving"] = "Salvando saídas", ["step_finished"] = "Finalizando operação", ["step_error"] = "Verificando erro",
            ["status_ready"] = "Pronto", ["ready_message"] = "Selecione uma pasta de origem para começar.", ["source_selected"] = "Pasta de origem selecionada.", ["language_updated"] = "Idioma atualizado.",
            ["source_required"] = "Origem obrigatória", ["source_required_message"] = "Escolha uma pasta de origem antes de iniciar.",
            ["running"] = "Processando", ["running_message"] = "O core Python está processando seus arquivos.", ["completed"] = "Concluído", ["completed_message"] = "Finalizado em {0:mm\\:ss}.",
            ["completed_errors"] = "Concluído com erros", ["exit_code_message"] = "O core Python encerrou com código {0}.", ["canceled"] = "Cancelado", ["canceled_message"] = "A operação foi cancelada.",
            ["could_not_start"] = "Não foi possível iniciar", ["destination_unavailable"] = "Destino indisponível", ["destination_unavailable_message"] = "Escolha uma pasta de destino existente primeiro.",
            ["start_organize"] = "Organizar", ["start_convert"] = "Converter", ["start_enhance"] = "Aprimorar"
        },
        ["es-ES"] = new()
        {
            ["nav_organize"] = "Organizar", ["nav_convert"] = "Convertir", ["nav_enhance"] = "Mejorar", ["nav_settings"] = "Configuración",
            ["pane_subtitle"] = "Herramientas multimedia con Python", ["brand_description"] = "Encuentre imágenes duplicadas, convierta medios y mejore imágenes localmente.",
            ["organize_title"] = "Organizar imágenes", ["organize_description"] = "Encuentre duplicados visuales y estandarice nombres con el núcleo Python.",
            ["convert_title"] = "Convertir archivos", ["convert_description"] = "Convierta imágenes y videos con el núcleo Python conservando los originales.",
            ["enhance_title"] = "Mejorar imágenes", ["enhance_description"] = "Ejecute mejora local con Real-ESRGAN sin mover los originales.",
            ["settings_title"] = "Configuración", ["settings_description"] = "Personalice Similaris, revise licencias y apoye el desarrollo.",
            ["cancel"] = "Cancelar", ["choose"] = "Elegir...", ["choose_files"] = "Elegir archivos...", ["clear"] = "Limpiar", ["copy"] = "Copiar", ["view"] = "Ver", ["close"] = "Cerrar", ["donate"] = "Hacer una donación",
            ["source"] = "Origen", ["source_description"] = "Elija la carpeta que procesará el núcleo Python.", ["source_files_description"] = "Elija archivos específicos que procesará el núcleo Python.",
            ["source_placeholder"] = "Ningún origen seleccionado", ["source_files_placeholder"] = "Ningún archivo seleccionado", ["source_mode_folder"] = "Carpeta", ["source_mode_files"] = "Archivos",
            ["source_files_selected"] = "{0} archivos seleccionados", ["source_files_selected_status"] = "Archivos de origen seleccionados.",
            ["destination"] = "Destino", ["destination_description"] = "Déjelo vacío para usar el destino predeterminado de la operación.", ["destination_placeholder"] = "Destino predeterminado",
            ["organize_section_title"] = "Organización de imágenes", ["organize_section_description"] = "Separe imágenes duplicadas y, opcionalmente, estandarice los nombres de archivo.",
            ["rename_files"] = "Estandarizar nombres de archivo", ["rename_prefix"] = "Prefijo", ["rename_example"] = "Ejemplo: img (1).jpg",
            ["sensitivity"] = "Sensibilidad", ["sensitivity_safer"] = "Más segura", ["sensitivity_balanced"] = "Equilibrada", ["sensitivity_broader"] = "Más amplia",
            ["sensitivity_safer_description"] = "Más estricta.", ["sensitivity_balanced_description"] = "Recomendada.", ["sensitivity_broader_description"] = "Más hallazgos.",
            ["convert_section_title"] = "Conversión de archivos", ["convert_section_description"] = "Elija un tipo de medio y cree copias convertidas conservando los originales.",
            ["conversion_type"] = "Tipo de conversión", ["convert_images"] = "Imágenes", ["convert_videos"] = "Videos", ["image_format"] = "Formato de imagen", ["video_format"] = "Formato de video", ["jpg_quality"] = "Calidad de imagen", ["video_quality"] = "Calidad de video",
            ["enhance_section_title"] = "Mejora de imágenes", ["enhance_section_description"] = "Ejecute Real-ESRGAN localmente mediante el núcleo Python.",
            ["upscale"] = "Ampliación", ["image_type"] = "Tipo de imagen", ["photo"] = "Foto", ["illustration"] = "Ilustración",
            ["appearance_title"] = "Apariencia e idioma", ["appearance_description"] = "Personalice Similaris y elija el idioma usado por el núcleo Python.",
            ["appearance_tab"] = "Apariencia", ["support_tab"] = "Apoyar", ["licenses_tab"] = "Licencias",
            ["language"] = "Idioma", ["theme"] = "Tema", ["theme_system"] = "Sistema", ["theme_light"] = "Claro", ["theme_dark"] = "Oscuro",
            ["support_title"] = "Apoye el desarrollo de Similaris", ["support_description"] = "Similaris es gratuito y se desarrolla de forma independiente. Las contribuciones ayudan a mantener el proyecto actualizado.",
            ["licenses_title"] = "Licencias", ["licenses_description"] = "Revise las licencias incluidas con Similaris y componentes de terceros.", ["licenses_missing"] = "No se encontraron los avisos de licencia.",
            ["processing_log"] = "Registro de procesamiento", ["log_placeholder"] = "La salida del núcleo aparecerá aquí.", ["open_destination"] = "Abrir destino",
            ["core_idle"] = "Núcleo Python inactivo", ["core_running"] = "Núcleo Python en ejecución",
            ["progress"] = "Progreso", ["progress_pending"] = "Calculando...", ["progress_error"] = "Error", ["progress_canceled"] = "Cancelado",
            ["waiting_to_start"] = "Esperando inicio.", ["starting"] = "Iniciando el núcleo Python...",
            ["view_log"] = "Ver registro de ejecución", ["step_processing"] = "Procesando archivos", ["step_analyzing"] = "Analizando archivos",
            ["step_comparing"] = "Comparando similitud visual", ["step_converting"] = "Convirtiendo medios", ["step_enhancing"] = "Mejorando imágenes",
            ["step_validating"] = "Validando resultados", ["step_saving"] = "Guardando salidas", ["step_finished"] = "Finalizando operación", ["step_error"] = "Revisando error",
            ["status_ready"] = "Listo", ["ready_message"] = "Seleccione una carpeta de origen para comenzar.", ["source_selected"] = "Carpeta de origen seleccionada.", ["language_updated"] = "Idioma actualizado.",
            ["source_required"] = "Origen obligatorio", ["source_required_message"] = "Elija una carpeta de origen antes de iniciar.",
            ["running"] = "Procesando", ["running_message"] = "El núcleo Python está procesando sus archivos.", ["completed"] = "Completado", ["completed_message"] = "Finalizado en {0:mm\\:ss}.",
            ["completed_errors"] = "Completado con errores", ["exit_code_message"] = "El núcleo Python terminó con código {0}.", ["canceled"] = "Cancelado", ["canceled_message"] = "La operación fue cancelada.",
            ["could_not_start"] = "No se pudo iniciar", ["destination_unavailable"] = "Destino no disponible", ["destination_unavailable_message"] = "Elija primero una carpeta de destino existente.",
            ["start_organize"] = "Organizar", ["start_convert"] = "Convertir", ["start_enhance"] = "Mejorar"
        }
    };
}
