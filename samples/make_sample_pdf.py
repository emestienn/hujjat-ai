"""Generate samples/student-handbook.pdf, a fictional bilingual handbook to demo Hujjat AI.

Usage: python samples/make_sample_pdf.py   (needs: pip install fpdf2)
"""

from pathlib import Path

from fpdf import FPDF

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

PAGES = [
    (
        "Orion Digital University: Student Handbook 2026/27",
        [
            "This handbook explains the main academic rules for Master's and Bachelor's students "
            "at Orion Digital University, a fictional university used to demonstrate Hujjat AI.",
            "1. Tuition payment. Tuition for the academic year is 24,000,000 UZS for Master's "
            "programmes and 18,000,000 UZS for Bachelor's programmes. It can be paid in full or in "
            "two equal instalments. The first instalment is due by 15 September and the second by "
            "15 February. A late fee of 1% per week is charged after each deadline.",
            "2. Students who have not paid the first instalment by 1 October cannot sit midterm "
            "exams until the balance is cleared with the Finance Office (room 104).",
        ],
    ),
    (
        "Attendance and exams",
        [
            "3. Attendance. Students must attend at least 80% of lectures and tutorials in each "
            "course. Students below 80% attendance are not admitted to the final exam and must "
            "retake the course.",
            "4. Grading. The final grade is made up of: midterm exam 30%, coursework and "
            "assignments 30%, final exam 40%. The pass mark is 60 out of 100.",
            "5. Retakes. A student who fails a final exam may retake it once, within four weeks "
            "after results are published. The retake fee is 500,000 UZS per course. The maximum "
            "grade after a retake is 70.",
            "6. Medical absence. If a student misses an exam because of illness, a medical "
            "certificate must be submitted to the Dean's office within 3 working days.",
        ],
    ),
    (
        "Talabalar uchun qo‘llanma (o‘zbek tilida)",
        [
            "7. Stipendiya. A’lo baholarga o‘qigan talabalarga oyiga 1 200 000 so‘m miqdorida "
            "stipendiya beriladi. Stipendiya olish uchun semestr o‘rtacha bahosi kamida 85 ball "
            "bo‘lishi va qarzdorlik bo‘lmasligi kerak.",
            "8. Kutubxona. Universitet kutubxonasi dushanbadan shanbagacha soat 08:00 dan 21:00 "
            "gacha ishlaydi. Talaba bir vaqtning o‘zida 5 tagacha kitob olishi mumkin, muddat "
            "14 kun.",
            "9. Yotoqxona. Yotoqxonada joy olish uchun ariza har yili 1 avgustgacha topshiriladi. "
            "Birinchi navbatda boshqa viloyatlardan kelgan birinchi kurs talabalariga joy beriladi.",
        ],
    ),
    (
        "Master's thesis",
        [
            "10. Thesis topic. Master's students choose a thesis topic with their supervisor by the "
            "end of the second semester. The topic must be approved by the department.",
            "11. Thesis defence. The thesis is 60-80 pages long and is defended in front of a "
            "committee of at least three members. Students must pass a plagiarism check with at "
            "least 75% originality before the defence.",
            "12. Contacts. Dean's office: dean@orion-university.example, room 210. Finance Office: "
            "finance@orion-university.example, room 104.",
        ],
    ),
]


def main() -> None:
    pdf = FPDF()
    pdf.add_font("DejaVu", "", FONT)
    pdf.add_font("DejaVu", "B", FONT_BOLD)
    pdf.set_auto_page_break(auto=True, margin=18)
    for title, paragraphs in PAGES:
        pdf.add_page()
        pdf.set_font("DejaVu", "B", 16)
        pdf.multi_cell(0, 9, title)
        pdf.ln(4)
        pdf.set_font("DejaVu", "", 11)
        for p in paragraphs:
            pdf.multi_cell(0, 6.5, p)
            pdf.ln(3)
    out = Path(__file__).parent / "student-handbook.pdf"
    pdf.output(str(out))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
