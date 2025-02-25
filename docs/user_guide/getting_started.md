# Getting Started with Scout

This guide will help you get familiar with the Scout application interface and basic functionality. After following the [installation instructions](installation.md), this guide will walk you through the first steps of using the application.

## First Launch

When you first launch Scout, you'll see the main application window with several tabs for different functionalities. The application starts with the Detection tab active by default.

![Main Window](../images/main_window.png)

If this is your first time using Scout, you'll need to select a game window to work with.

## Selecting a Game Window

1. Click on the **Window** menu at the top of the application.
2. Select **Select Window** from the dropdown menu.
3. A dialog will appear showing a list of available windows.
4. Select the Total Battle window from the list. It may appear as:
   - "Total Battle" (for the standalone app)
   - Browser title with "Total Battle" (for the browser version)
5. Click **OK** to confirm your selection.

![Window Selection](../images/window_selection.png)

Once a window is selected, Scout will begin capturing from that window and you'll see a status message confirming the selection.

## User Interface Overview

Let's take a look at the main components of the Scout interface:

### Main Menu

The menu bar at the top of the application provides access to various functions:

- **File**: Options for opening, saving, and exporting data.
- **Window**: Controls for selecting and managing game windows.
- **Tools**: Access to additional tools and utilities.
- **View**: Options for customizing the application appearance.
- **Help**: Documentation, information, and support resources.

### Tab Bar

The main tab bar allows you to switch between different functional areas of the application:

- **Detection**: Find and analyze game elements using computer vision.
- **Automation**: Create and run sequences of automated actions.
- **Game State**: Monitor and analyze the game state over time.
- **Settings**: Configure application behavior and preferences.

### Status Bar

The status bar at the bottom of the window shows:

- Current window status (connected/disconnected)
- Last detection results
- Memory usage
- Application status messages

## Detection Tab

The Detection tab is where you can identify game elements using various detection methods.

![Detection Tab](../images/detection_tab.png)

Key components of this tab include:

1. **Detection Strategy**: Choose between Template Matching, OCR, or YOLO detection.
2. **Templates List**: Select templates to use for detection (for Template Matching).
3. **Detection Parameters**: Configure threshold, region, and other settings.
4. **Run Button**: Execute the detection with current settings.
5. **Results View**: Displays detection results visually on the captured image.
6. **Results Table**: Lists all detected elements with positions and confidence scores.

### Basic Detection Example

Let's perform a simple template matching detection:

1. In the Detection Tab, ensure "Template Matching" is selected in the Detection Strategy dropdown.
2. Select one or more templates from the template list. (If no templates exist yet, see [Creating Templates](#creating-templates) below).
3. Set the Confidence Threshold to 70%.
4. Click the **Run Detection** button.
5. The results will appear in the results view and table.

## Automation Tab

The Automation tab enables you to create and run sequences of actions based on detection results.

![Automation Tab](../images/automation_tab.png)

Key components include:

1. **Sequence List**: Saved automation sequences.
2. **Action List**: Individual actions in the selected sequence.
3. **Action Editor**: Interface for adding and editing actions.
4. **Run Controls**: Buttons to run, pause, and stop the selected sequence.

### Creating a Simple Sequence

Here's how to create a basic automation sequence:

1. Click the **New** button to create a new sequence.
2. Enter a name for your sequence (e.g., "Click Resource").
3. Click **Add** to add a new action.
4. In the Action Editor, select "Click" as the Action Type.
5. Configure the click parameters:
   - Select "Template" for the Target Type.
   - Choose a template (e.g., a resource icon).
   - Set the click type (e.g., "Left Click").
6. Click **Apply** to add the action to your sequence.
7. Click **Save** to save your sequence.

To run the sequence, select it in the list and click the **Run** button.

## Game State Tab

The Game State tab displays information about the current game state, including resources, buildings, and map data.

![Game State Tab](../images/game_state_tab.png)

This tab has several views:

1. **Overview**: General game state information.
2. **Resources**: Current resource levels and production rates.
3. **Buildings**: List of buildings and their levels.
4. **Map**: Visualization of the game map.
5. **History**: Historical data tracking over time.

## Settings Tab

The Settings tab allows you to configure various aspects of the application.

![Settings Tab](../images/settings_tab.png)

Key setting categories include:

1. **UI**: Language, theme, and general UI settings.
2. **Window**: Window capture methods and display settings.
3. **Detection**: Default detection parameters and strategies.
4. **OCR**: Tesseract OCR configuration.
5. **Paths**: Locations for saving files and resources.
6. **Advanced**: Advanced configuration options.
7. **Notifications**: Sound and visual notification settings.

## Creating Templates

Templates are image snippets used for detecting elements in the game. Here's how to create a new template:

1. Go to the **Tools** menu and select **Template Creator**.
2. The Template Creator dialog will open.
3. Click **Capture** to take a new screenshot of the game window.
4. Use your mouse to draw a rectangle around the element you want to create a template for.
5. Enter a name for the template (e.g., "GoldMine").
6. Click **Save Template**.

![Template Creator](../images/template_creator.png)

Your new template will now appear in the template list in the Detection Tab.

## Basic Workflow Example

Let's put everything together with a basic workflow example for detecting and clicking on a resource:

1. Create a template for the resource (e.g., gold mine) using the Template Creator.
2. In the Detection Tab, select Template Matching and your new template.
3. Run the detection to verify that the resource is found correctly.
4. Switch to the Automation Tab and create a new sequence.
5. Add a "Click" action targeting the template you created.
6. Save and run the sequence.
7. The application will detect the resource and click on it automatically.

## Keyboard Shortcuts

Scout has several keyboard shortcuts for common operations:

- **Ctrl+N**: Create new sequence
- **Ctrl+O**: Open sequence
- **Ctrl+S**: Save sequence
- **F5**: Run detection
- **F6**: Run automation
- **F9**: Capture screenshot
- **Esc**: Stop running operations

You can view all available shortcuts by going to **Help** → **Keyboard Shortcuts**.

## Next Steps

Now that you're familiar with the basic functionality of Scout, you can explore more advanced features:

- Learn about different [detection methods](detection.md)
- Explore [automation actions](automation.md) for complex sequences
- Set up [game state monitoring](game_state.md)
- Customize [application settings](settings.md) for optimal performance

If you encounter any issues, refer to the [Troubleshooting](troubleshooting.md) section or check the [FAQ](faq.md) for common questions. 