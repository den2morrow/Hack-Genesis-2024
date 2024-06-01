FROM python
COPY requirement.txt .
RUN python -m pip install -r requirement.txt
COPY . .
ENTRYPOINT ["python"]
CMD ["./your_script_name.py"]