"""Dream.OS Task Monitoring Widgets."""

from datetime import datetime
from typing import Dict, Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QProgressBar, QScrollArea, QFrame, QPushButton
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from core.gui.theme import DreamTheme
from core.coordination.cursor.task_execution_state_machine import TaskState, StepState

class TaskStepWidget(QFrame):
    """Widget displaying a single task step's status."""
    
    def __init__(self, step_data: Dict, parent=None):
        super().__init__(parent)
        self.setObjectName("TaskStep")
        self.setFrameStyle(QFrame.StyledPanel)
        
        self.step_data = step_data
        self._setup_ui()
        self.apply_theme()
    
    def _setup_ui(self):
        """Setup the widget UI."""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Header with action type and element
        header = QHBoxLayout()
        
        self.action_label = QLabel(f"Action: {self.step_data['action']}")
        self.action_label.setObjectName("StepAction")
        header.addWidget(self.action_label)
        
        if self.step_data.get('element'):
            self.element_label = QLabel(f"Element: {self.step_data['element']}")
            self.element_label.setObjectName("StepElement")
            header.addWidget(self.element_label)
        
        header.addStretch()
        layout.addLayout(header)
        
        # Status and timing
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel(self.step_data['state'])
        self.status_label.setObjectName("StepStatus")
        status_layout.addWidget(self.status_label)
        
        if self.step_data.get('result'):
            result = self.step_data['result']
            if result.get('success'):
                duration = result.get('duration', 0)
                self.duration_label = QLabel(f"Duration: {duration:.2f}s")
                self.duration_label.setObjectName("StepDuration")
                status_layout.addWidget(self.duration_label)
            else:
                self.error_label = QLabel(f"Error: {result.get('message', 'Unknown error')}")
                self.error_label.setObjectName("StepError")
                status_layout.addWidget(self.error_label)
        
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        # Timing info
        if self.step_data.get('started_at'):
            timing = QHBoxLayout()
            started = datetime.fromisoformat(self.step_data['started_at'])
            
            self.started_label = QLabel(f"Started: {started.strftime('%H:%M:%S')}")
            self.started_label.setObjectName("StepTiming")
            timing.addWidget(self.started_label)
            
            if self.step_data.get('completed_at'):
                completed = datetime.fromisoformat(self.step_data['completed_at'])
                self.completed_label = QLabel(f"Completed: {completed.strftime('%H:%M:%S')}")
                self.completed_label.setObjectName("StepTiming")
                timing.addWidget(self.completed_label)
            
            timing.addStretch()
            layout.addLayout(timing)
    
    def apply_theme(self):
        """Apply Dream.OS theme to the widget."""
        self.setStyleSheet(f"""
            #TaskStep {{
                background-color: {DreamTheme.SURFACE};
                border-radius: 4px;
                padding: 8px;
                margin: 2px;
            }}
            #StepAction {{
                color: {DreamTheme.TEXT};
                font-weight: bold;
            }}
            #StepElement {{
                color: {DreamTheme.TEXT_SECONDARY};
            }}
            #StepStatus {{
                font-weight: bold;
            }}
            #StepDuration {{
                color: {DreamTheme.TEXT_SECONDARY};
            }}
            #StepError {{
                color: {DreamTheme.ERROR};
            }}
            #StepTiming {{
                color: {DreamTheme.TEXT_SECONDARY};
                font-size: 10px;
            }}
        """)
        
        # Apply state-specific colors
        state = self.step_data['state'].lower()
        state_colors = {
            'pending': DreamTheme.TEXT_SECONDARY,
            'running': DreamTheme.PRIMARY,
            'retrying': DreamTheme.WARNING,
            'completed': DreamTheme.SUCCESS,
            'failed': DreamTheme.ERROR,
            'skipped': DreamTheme.TEXT_DISABLED
        }
        self.status_label.setStyleSheet(
            f"color: {state_colors.get(state, DreamTheme.TEXT)};"
        )
    
    def update_data(self, step_data: Dict):
        """Update widget with new step data."""
        self.step_data = step_data
        # Recreate UI with new data
        self._setup_ui()
        self.apply_theme()

class TaskWidget(QFrame):
    """Widget displaying a complete task's execution status."""
    
    state_changed = pyqtSignal(str, str)  # task_id, new_state
    
    def __init__(self, task_data: Dict, parent=None):
        super().__init__(parent)
        self.setObjectName("Task")
        self.setFrameStyle(QFrame.StyledPanel)
        
        self.task_data = task_data
        self.task_id = task_data['task_id']
        self.task_state = TaskState(task_data['state'])
        
        self._setup_ui()
        self.apply_theme()
    
    def _setup_ui(self):
        """Setup the widget UI."""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Task header
        header = QHBoxLayout()
        
        self.task_label = QLabel(f"Task: {self.task_data['task_id']}")
        self.task_label.setObjectName("TaskId")
        header.addWidget(self.task_label)
        
        self.state_label = QLabel(self.task_data['state'])
        self.state_label.setObjectName("TaskState")
        header.addWidget(self.state_label)
        
        if self.task_data.get('cursor_instance_id'):
            self.instance_label = QLabel(f"Instance: {self.task_data['cursor_instance_id']}")
            self.instance_label.setObjectName("TaskInstance")
            header.addWidget(self.instance_label)
        
        # Control buttons
        self.controls_layout = QHBoxLayout()
        
        if self.task_state in [TaskState.RUNNING, TaskState.PREPARING]:
            self.pause_button = QPushButton("Pause")
            self.pause_button.setObjectName("TaskControl")
            self.controls_layout.addWidget(self.pause_button)
            
            self.cancel_button = QPushButton("Cancel")
            self.cancel_button.setObjectName("TaskControl")
            self.controls_layout.addWidget(self.cancel_button)
        
        header.addLayout(self.controls_layout)
        header.addStretch()
        layout.addLayout(header)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setObjectName("TaskProgress")
        total_steps = len(self.task_data['steps'])
        completed_steps = sum(1 for s in self.task_data['steps'] 
                            if s['state'] in ['completed', 'skipped'])
        self.progress.setMaximum(total_steps)
        self.progress.setValue(completed_steps)
        layout.addWidget(self.progress)
        
        # Steps
        steps_widget = QWidget()
        steps_layout = QVBoxLayout()
        steps_widget.setLayout(steps_layout)
        
        for step in self.task_data['steps']:
            step_widget = TaskStepWidget(step)
            steps_layout.addWidget(step_widget)
        
        steps_scroll = QScrollArea()
        steps_scroll.setObjectName("TaskSteps")
        steps_scroll.setWidget(steps_widget)
        steps_scroll.setWidgetResizable(True)
        layout.addWidget(steps_scroll)
        
        # Error message if any
        if self.task_data.get('error_message'):
            self.error_label = QLabel(f"Error: {self.task_data['error_message']}")
            self.error_label.setObjectName("TaskError")
            layout.addWidget(self.error_label)
    
    def apply_theme(self):
        """Apply Dream.OS theme to the widget."""
        self.setStyleSheet(f"""
            #Task {{
                background-color: {DreamTheme.SURFACE};
                border-radius: 8px;
                padding: 12px;
                margin: 4px;
            }}
            #TaskId {{
                color: {DreamTheme.TEXT};
                font-size: 14px;
                font-weight: bold;
            }}
            #TaskState {{
                font-weight: bold;
            }}
            #TaskInstance {{
                color: {DreamTheme.TEXT_SECONDARY};
            }}
            #TaskProgress {{
                background-color: {DreamTheme.BACKGROUND};
                border: none;
                border-radius: 2px;
                height: 8px;
                margin: 8px 0;
            }}
            #TaskProgress::chunk {{
                background-color: {DreamTheme.PRIMARY};
                border-radius: 2px;
            }}
            #TaskSteps {{
                border: none;
                background-color: transparent;
            }}
            #TaskError {{
                color: {DreamTheme.ERROR};
                font-weight: bold;
                padding: 8px;
            }}
            #TaskControl {{
                background-color: {DreamTheme.SURFACE_VARIANT};
                color: {DreamTheme.TEXT};
                border: none;
                border-radius: 4px;
                padding: 4px 12px;
            }}
            #TaskControl:hover {{
                background-color: {DreamTheme.PRIMARY_VARIANT};
            }}
        """)
        
        # Apply state-specific colors
        state = self.task_data['state'].lower()
        state_colors = {
            'pending': DreamTheme.TEXT_SECONDARY,
            'preparing': DreamTheme.INFO,
            'running': DreamTheme.PRIMARY,
            'paused': DreamTheme.WARNING,
            'completed': DreamTheme.SUCCESS,
            'failed': DreamTheme.ERROR,
            'cancelled': DreamTheme.TEXT_DISABLED
        }
        self.state_label.setStyleSheet(
            f"color: {state_colors.get(state, DreamTheme.TEXT)};"
        )
        
        if state == 'running':
            self.progress.setStyleSheet(f"""
                #TaskProgress::chunk {{
                    background-color: {DreamTheme.PRIMARY};
                }}
            """)
        elif state == 'completed':
            self.progress.setStyleSheet(f"""
                #TaskProgress::chunk {{
                    background-color: {DreamTheme.SUCCESS};
                }}
            """)
        elif state in ['failed', 'cancelled']:
            self.progress.setStyleSheet(f"""
                #TaskProgress::chunk {{
                    background-color: {DreamTheme.ERROR};
                }}
            """)
    
    def update_data(self, task_data: Dict):
        """Update widget with new task data."""
        old_state = self.task_state
        self.task_data = task_data
        self.task_state = TaskState(task_data['state'])
        
        # Recreate UI with new data
        self._setup_ui()
        self.apply_theme()
        
        # Emit state change if needed
        if old_state != self.task_state:
            self.state_changed.emit(self.task_id, self.task_state.value) 