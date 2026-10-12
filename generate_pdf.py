import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#718096"))
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 54, 36, page_text)
        self.drawString(54, 36, "Lamp Robot Character Simulation — Ubuntu 24.04 Deployment Guide")
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(54, 48, letter[0] - 54, 48)
        self.restoreState()

def build_pdf(filename="UBUNTU_DEPLOYMENT_INSTRUCTIONS.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    primary_color = colors.HexColor("#1A365D")  # Deep Navy
    accent_color = colors.HexColor("#2B6CB0")   # Slate Blue
    dark_text = colors.HexColor("#2D3748")      # Charcoal Body
    code_bg = colors.HexColor("#F7FAFC")        # Off white
    box_bg = colors.HexColor("#EBF8FF")         # Light Blue Box
    box_border = colors.HexColor("#BEE3F8")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=primary_color,
        spaceAfter=6,
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#4A5568"),
        spaceAfter=15,
    )

    h1_style = ParagraphStyle(
        'H1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=6,
    )

    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=accent_color,
        spaceBefore=8,
        spaceAfter=4,
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=dark_text,
        spaceAfter=6,
    )

    bullet_style = ParagraphStyle(
        'Bullet',
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=3,
    )

    code_style = ParagraphStyle(
        'CodeBlock',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#1A202C"),
        backColor=code_bg,
        borderPadding=6,
        spaceBefore=4,
        spaceAfter=6,
    )

    box_text_style = ParagraphStyle(
        'BoxText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#2C5282"),
    )

    story = []

    # Title Banner
    story.append(Paragraph("5-DOF Lamp Robot Character Simulation", title_style))
    story.append(Paragraph("Complete Setup, Deployment & Testing Guide for Ubuntu 24.04 Virtual Machines", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceBefore=0, spaceAfter=12))

    # Overview Box
    overview_text = (
        "<b>System Summary:</b> This project implements a fully offline, expressive 5-DOF lamp robot character. "
        "The architecture features a strict JSON protocol over a <b>TCP socket transport boundary</b>, an authoritative "
        "body receiver enforcing whole-command timeouts and enum limits, local AI models (Vosk for offline STT, Moondream for VLM vision, "
        "and Qwen2:0.5B for cognitive reasoning), cross-platform multi-modal audio/light synthesis, and a goal-directed observe-act-reobserve path."
    )
    overview_table = Table([[Paragraph(overview_text, box_text_style)]], colWidths=[504])
    overview_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), box_bg),
        ('BOX', (0,0), (-1,-1), 1, box_border),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(overview_table)
    story.append(Spacer(1, 10))

    # Section 1: Target Environment
    story.append(Paragraph("1. Target Environment & Hardware Requirements", h1_style))
    story.append(Paragraph("The system is optimized for a clean <b>Ubuntu 24.04 LTS</b> virtual machine (VMware, VirtualBox, KVM, or WSL2):", body_style))
    story.append(Paragraph("• <b>CPU:</b> 4 vCPU cores (x86_64)", bullet_style))
    story.append(Paragraph("• <b>Memory:</b> 8 GB RAM (runs comfortably without swap thrashing)", bullet_style))
    story.append(Paragraph("• <b>GPU:</b> No discrete GPU or CUDA required (all models run on CPU)", bullet_style))
    story.append(Paragraph("• <b>Peripherals:</b> Virtual or physical webcam, microphone, and audio speaker", bullet_style))
    story.append(Spacer(1, 8))

    # Section 2: Step-by-Step Ubuntu VM Setup
    story.append(Paragraph("2. Ubuntu System Prerequisites & Packages", h1_style))
    story.append(Paragraph("Open a terminal on your Ubuntu machine and install the required build tools, audio, video, and TTS packages:", body_style))
    story.append(Paragraph(
        "sudo apt update<br/>"
        "sudo apt install -y python3-pip python3-dev portaudio19-dev espeak-ng ffmpeg alsa-utils unzip wget curl git",
        code_style
    ))
    story.append(Spacer(1, 8))

    # Section 3: Python Environment
    story.append(Paragraph("3. Extracting Project & Installing Dependencies", h1_style))
    story.append(Paragraph("Unzip the provided submission archive and install the Python dependencies:", body_style))
    story.append(Paragraph(
        "unzip submission.zip -d lamp_robot<br/>"
        "cd lamp_robot<br/>"
        "pip3 install -r requirements.txt --break-system-packages",
        code_style
    ))
    story.append(Paragraph("<i>Note: On Ubuntu 24.04, Python 3.12+ enforces PEP 668. You can use a virtual environment or <code>--break-system-packages</code>.</i>", body_style))
    story.append(Spacer(1, 8))

    # Section 4: Offline Models Installation
    story.append(Paragraph("4. Local Model Downloads (Vosk + Ollama)", h1_style))
    story.append(Paragraph("<b>A. Offline Audio Speech Recognition (Vosk)</b>", h2_style))
    story.append(Paragraph("Download and extract the lightweight English speech model into the <code>model/</code> directory:", body_style))
    story.append(Paragraph(
        "wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip<br/>"
        "unzip vosk-model-small-en-us-0.15.zip<br/>"
        "mv vosk-model-small-en-us-0.15 model<br/>"
        "rm vosk-model-small-en-us-0.15.zip",
        code_style
    ))

    story.append(Paragraph("<b>B. Local Vision & Cognition Models (Ollama)</b>", h2_style))
    story.append(Paragraph("Install Ollama and pull the required tiny vision and language models:", body_style))
    story.append(Paragraph(
        "curl -fsSL https://ollama.com/install.sh | sh<br/>"
        "# Verify Ollama is active<br/>"
        "ollama pull moondream<br/>"
        "ollama pull qwen2:0.5b",
        code_style
    ))
    story.append(Spacer(1, 8))

    # Section 5: Running the System
    story.append(Paragraph("5. Running the Character Robot Simulation", h1_style))
    story.append(Paragraph("Start the complete autonomous character loop with:", body_style))
    story.append(Paragraph("python3 main.py", code_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>Virtual Machine Environment Flags:</b>", h2_style))
    story.append(Paragraph("• <code>FORCE_ENGAGEMENT=1</code>: Bypasses webcam face detection and simulates active face engagement. Essential for headless servers, VMs without camera pass-through, or test scripts.", bullet_style))
    story.append(Paragraph("• <code>PYBULLET_DIRECT=1</code>: Runs PyBullet physics and kinematics in direct headless mode without creating an X11 window.", bullet_style))
    story.append(Paragraph("Example for testing in a VM without a physical camera:", body_style))
    story.append(Paragraph("FORCE_ENGAGEMENT=1 python3 main.py", code_style))
    story.append(Spacer(1, 8))

    # Section 6: Unit & Integration Tests
    story.append(Paragraph("6. Running the Automated Test Suite", h1_style))
    story.append(Paragraph("The submission includes 21 comprehensive unit and integration tests across 5 test suites:", body_style))
    story.append(Paragraph("python3 -m unittest discover -s tests -v", code_style))

    # Table of tests
    test_table_data = [
        [Paragraph("<b>Test Module</b>", body_style), Paragraph("<b>Coverage Area</b>", body_style), Paragraph("<b>Key Verifications</b>", body_style)],
        [Paragraph("<code>test_protocol.py</code>", body_style), Paragraph("JSON Protocol & Schema", body_style), Paragraph("Command/result round-trip, enum validation, safe intent clamping, timeout limits.", body_style)],
        [Paragraph("<code>test_transport.py</code>", body_style), Paragraph("TCP Socket Boundary", body_style), Paragraph("Client/server message exchange over loopback TCP, timeout handling, rejection handling.", body_style)],
        [Paragraph("<code>test_body_receiver.py</code>", body_style), Paragraph("Authoritative Receiver", body_style), Paragraph("Sequence number checking, status tracking, whole-command timeout reporting, hardware safety.", body_style)],
        [Paragraph("<code>test_action_controller.py</code>", body_style), Paragraph("Multi-Modal Body Controller", body_style), Paragraph("PyBullet motion execution, light cues, PCM audio synthesis for Linux, TTS budget.", body_style)],
        [Paragraph("<code>test_runtime_and_verification.py</code>", body_style), Paragraph("Cognition & Verification", body_style), Paragraph("Target extraction, dynamic scene-aware search planning, completion verification.", body_style)],
    ]
    test_table = Table(test_table_data, colWidths=[130, 130, 244])
    test_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EDF2F7")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(test_table)
    story.append(Spacer(1, 10))

    # Section 7: Interaction Moments & Telemetry
    story.append(Paragraph("7. Demonstration Moments & Raw Measurements", h1_style))
    story.append(Paragraph(
        "Each interaction records rich telemetry into <code>measurements.jsonl</code>. The system demonstrates 5 core moments:",
        body_style
    ))
    story.append(Paragraph("1. <b>Engagement:</b> Face detection triggers awareness; disengages when user leaves.", bullet_style))
    story.append(Paragraph("2. <b>Character Response:</b> Intentional combination of motion (nod/search), warm/success lights, audio sound cues (chirp/confirm), and speech.", bullet_style))
    story.append(Paragraph("3. <b>Spoken Interaction:</b> Vosk offline STT transcribes microphone audio; TTS speaks responses.", bullet_style))
    story.append(Paragraph("4. <b>Scene Memory:</b> Moondream vision analyzes live camera frames; answers spoken questions referencing memory.", bullet_style))
    story.append(Paragraph("5. <b>Goal-Directed Action:</b> Evaluates goal target against live vision, searches scene dynamically if missing, and validates post-observation state.", bullet_style))
    story.append(Spacer(1, 8))

    # Section 8: Troubleshooting
    story.append(Paragraph("8. Troubleshooting & Common VM Issues", h1_style))
    trouble_data = [
        [Paragraph("<b>Issue</b>", body_style), Paragraph("<b>Likely Cause</b>", body_style), Paragraph("<b>Solution</b>", body_style)],
        [Paragraph("Connection refused on port 8765", body_style), Paragraph("Server starting or port conflict", body_style), Paragraph("Wait 1s for server bind or check port with <code>lsof -i :8765</code>.", body_style)],
        [Paragraph("Ollama model query fails", body_style), Paragraph("Ollama daemon not running", body_style), Paragraph("Run <code>ollama serve</code> or check <code>systemctl status ollama</code>.", body_style)],
        [Paragraph("Vosk STT skipped / silent", body_style), Paragraph("Missing 'model' folder", body_style), Paragraph("Ensure Vosk model is unpacked at <code>./model</code>.", body_style)],
        [Paragraph("No audio sound in VM", body_style), Paragraph("VM audio device disabled", body_style), Paragraph("Enable Intel HD Audio or ALSA in VM hypervisor settings.", body_style)],
    ]
    trouble_table = Table(trouble_data, colWidths=[130, 130, 244])
    trouble_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EDF2F7")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(trouble_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Generated PDF: {filename}")

if __name__ == "__main__":
    build_pdf()
