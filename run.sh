# Use cron tab to set it up
# @reboot sleep 30 && /home/pi/edge-pi-poc/run.sh >> /home/pi/edge-pi-poc/out.txt 2>&1

project_path="/home/pi/edge-pi-poc"
output_path="/home/pi/edge-pi-poc/output.txt"
date_var=$(date +"%m/%d/%Y %H:%M:%S")

echo "\n${date_var} Running Edge data collection job..."
cd ${project_path}

activate () {
  . /home/pi/venv/bin/activate
}
activate

cd "src"
echo ${project_path}
python main.py
