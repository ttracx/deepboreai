import { useEffect, useState } from 'react'
import axios from 'axios'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  LineElement,
  PointElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend
} from 'chart.js'

ChartJS.register(LineElement, PointElement, CategoryScale, LinearScale, Tooltip, Legend)

function App() {
  const [data, setData] = useState(null)
  const [history, setHistory] = useState([])

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws")
    ws.onmessage = (event) => {
      const parsed = JSON.parse(event.data)
      setData(parsed)
      fetchHistory()
    }
    fetchHistory()
  }, [])

  const fetchHistory = async () => {
    const res = await axios.get("http://localhost:8000/history")
    setHistory(res.data)
  }

  const downloadCSV = () => {
    window.open("http://localhost:8000/export", "_blank")
  }

  const graphData = {
    labels: history.map(h => h.timestamp.slice(11, 19)),
    datasets: [
      {
        label: "ROP",
        data: history.map(h => h.predicted_rop),
        fill: false,
        borderColor: "blue",
        tension: 0.1
      }
    ]
  }

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold">Drilling Ops Dashboard</h1>

      {data && (
        <div className="mt-6 p-4 border rounded bg-white">
          <h2 className="text-xl font-semibold mb-2">Live Data</h2>
          <p><strong>Priority:</strong> {data.priority}</p>
          <p>Bit Depth: {data.bit_depth}</p>
          <p>Predicted ROP: {data.predicted_rop}</p>
          <p>Sticking Alerts: {data.mechanical_sticking_alert ? 'Yes' : 'No'}, {data.differential_sticking_alert ? 'Yes' : 'No'}</p>
          <p>Hole Cleaning Issue: {data.hole_cleaning_alert ? 'Yes' : 'No'}</p>
          <p>Mud Loss Risk: {data.mud_loss_alert ? 'Yes' : 'No'}</p>
          <p><small>{data.timestamp}</small></p>
        </div>
      )}

      <div className="mt-6">
        <h2 className="text-xl font-semibold mb-2">ROP Trend</h2>
        <Line data={graphData} />
      </div>

      <div className="mt-6">
        <h2 className="text-xl font-semibold mb-2">Recent History</h2>
        <button className="mb-2 px-4 py-2 bg-blue-600 text-white rounded" onClick={downloadCSV}>Export to CSV</button>
        <table className="w-full text-sm border">
          <thead>
            <tr>
              <th className="border px-2">Timestamp</th>
              <th className="border px-2">Bit Depth</th>
              <th className="border px-2">ROP</th>
              <th className="border px-2">Alerts</th>
            </tr>
          </thead>
          <tbody>
            {history.map((entry, idx) => (
              <tr key={idx} className="border">
                <td className="border px-2">{entry.timestamp}</td>
                <td className="border px-2">{entry.bit_depth}</td>
                <td className="border px-2">{entry.predicted_rop.toFixed(2)}</td>
                <td className="border px-2">
                  {entry.mechanical_sticking_alert && 'Mech '}
                  {entry.differential_sticking_alert && 'Diff '}
                  {entry.hole_cleaning_alert && 'Hole '}
                  {entry.mud_loss_alert && 'Mud'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default App