# Infographic Explainer Video Generator (No Audio)

## Usage
1. Place your infographic image at `assets/infographic.png`
2. Add point-wise explanation in `.txt` files like `point1.txt`, `point2.txt` in `assets/texts/`
3. Run:
```bash
pip install -r requirements.txt
python generate_video.py
```
Final video will be saved in `output/final_video.mp4`


Give me 4 points for financial tips in a json format such that each point should have a clear title in not more than 6 words. Each title should have description of three or four key points that explains the titles to the point short and precise. Consider a point is maximum a two liner text.

[
  {
    "title": "Build an Emergency Fund",
    "points": [
      "Save at least 3–6 months' expenses.",
      "Use a separate high-interest savings account.",
      "Start small, automate monthly contributions.",
      "Avoid dipping into it for non-emergencies."
    ],
    "position": {
      "x": 629.98547,
      "y": 219.97488
    }
  },
  {
    "title": "Track and Limit Expenses",
    "points": [
      "Use budgeting apps to monitor spending.",
      "Categorize and cut non-essential costs.",
      "Follow the 50-30-20 rule for budgeting.",
      "Review expenses weekly to stay on track."
    ],
    "position": {
      "x": 48.126694,
      "y": 638.68842
    }
  },
  {
    "title": "Invest Early and Regularly",
    "points": [
      "Start with index funds or SIPs.",
      "Leverage compound interest for long-term gains.",
      "Invest a fixed amount every month.",
      "Stay invested despite short-term market dips."
    ],
    "position": {
      "x": 629.98547,
      "y": 1029.7236
    }
  },
  {
    "title": "Clear High-Interest Debt Fast",
    "points": [
      "Prioritize credit cards and personal loans.",
      "Pay more than the minimum due monthly.",
      "Consider balance transfers or consolidation plans.",
      "Avoid new debt until existing is cleared."
    ],
    "position": {
      "x": 48.126694,
      "y": 1387.7136
    }
  }
]