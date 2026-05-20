@echo off
echo Criando ambiente virtual...
python -m venv .venv

echo Ativando ambiente...
call .venv\Scripts\activate.bat

echo Instalando dependencias...
pip install -r requirements.txt

echo.
echo Pronto. Para ativar o ambiente manualmente:
echo   .venv\Scripts\activate
echo.
echo Para subir o servidor:
echo   cd server ^&^& uvicorn main:app --reload
echo.
echo Para rodar o cliente (em outro terminal com .venv ativado):
echo   cd client ^&^& python main.py
pause
