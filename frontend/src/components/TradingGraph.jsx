import React, { useMemo } from 'react';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler
} from 'chart.js';
import { Line } from 'react-chartjs-2';

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler
);

// Custom plugin to draw B/S markers inside points
const markerPlugin = {
    id: 'markerPlugin',
    afterDatasetsDraw(chart) {
        const { ctx } = chart;
        chart.data.datasets.forEach((dataset, i) => {
            const meta = chart.getDatasetMeta(i);
            if (!meta.hidden) {
                meta.data.forEach((element, index) => {
                    const dataPoint = dataset.data[index];
                    if (dataPoint?.markerType) {
                        const { x, y } = element.tooltipPosition();
                        ctx.fillStyle = 'white';
                        ctx.font = 'bold 10px Arial';
                        ctx.textAlign = 'center';
                        ctx.textBaseline = 'middle';
                        ctx.fillText(dataPoint.markerType, x, y);
                    }
                });
            }
        });
    }
};

ChartJS.register(markerPlugin);

const TradingGraph = ({ transactionHistory = [], basePrice = 0 }) => {

    const chartData = useMemo(() => {
        // 1. Start point
        const startPoint = {
            x: 'Start',
            y: basePrice,
            basePrice: basePrice,
            execPrice: basePrice,
            pnl: 0,
            part: 'N/A',
            asset: 'N/A',
            action: 'start',
            markerType: null, // No text for start point
        };

        // 2. Transaction points
        const points = transactionHistory.map((tx, idx) => {
            // Determine Marker type (B or S)
            let mType = null;
            if (tx.action === 'buy') mType = 'B';
            if (tx.action === 'sell') mType = 'S';

            return {
                x: tx.timestamp || `Px ${idx + 1}`,
                y: tx.price,
                basePrice: tx.base_price_at_execution || basePrice,
                execPrice: tx.price,
                pnl: tx.pnl || 0,
                part: `${tx.part_number}/${tx.total_parts}`,
                asset: tx.token_symbol,
                action: tx.action,
                markerType: mType
            };
        });

        const dataPoints = [startPoint, ...points];

        return {
            labels: dataPoints.map(p => p.x),
            datasets: [
                {
                    label: 'Price Action',
                    data: dataPoints,
                    // Theme Colors: Lime / Neon Green
                    borderColor: '#bef264', // Lime-400 equivalent for "theme" look
                    backgroundColor: (context) => {
                        const ctx = context.chart.ctx;
                        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
                        gradient.addColorStop(0, 'rgba(190, 242, 100, 0.5)'); // Lime Glow
                        gradient.addColorStop(1, 'rgba(190, 242, 100, 0.0)');
                        return gradient;
                    },
                    borderWidth: 2,
                    tension: 0.4, // User requested "smooth" line
                    fill: true,
                    pointBackgroundColor: (context) => {
                        const index = context.dataIndex;
                        const point = context.dataset.data[index];
                        if (point.action === 'buy') return '#10b981'; // --success
                        if (point.action === 'sell') return '#ef4444'; // --danger
                        return '#475569'; // --text-faint
                    },
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 6,
                    pointHoverRadius: 8,
                },
            ],
        };
    }, [transactionHistory, basePrice]);

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: false,
            },
            tooltip: {
                backgroundColor: 'rgba(15, 23, 42, 0.9)', // --bg-deep/panel
                titleColor: '#f8fafc', // --text-main
                bodyColor: '#cbd5e1', // --text-muted
                borderColor: 'rgba(255, 255, 255, 0.1)',
                borderWidth: 1,
                padding: 12,
                displayColors: false,
                callbacks: {
                    title: (context) => {
                        const point = context[0].raw;
                        return point.action === 'start' ? 'Details' : `${point.action.toUpperCase()} - ${point.asset}`;
                    },
                    label: (context) => {
                        const point = context.raw;
                        if (point.action === 'start') {
                            return `Base Price: $${point.basePrice.toFixed(4)}`;
                        }
                        return [
                            `Base Price: $${Number(point.basePrice).toFixed(4)}`,
                            `Exec Price: $${Number(point.execPrice).toFixed(4)}`,
                            `P&L: ${point.pnl >= 0 ? '+' : ''}$${Number(point.pnl).toFixed(4)}`,
                            `Part: ${point.part}`,
                            `Asset: ${point.asset}`
                        ];
                    }
                }
            },
        },
        scales: {
            x: {
                grid: {
                    display: false,
                },
                ticks: {
                    color: '#94a3b8', // --text-muted
                    maxTicksLimit: 6,
                    font: {
                        family: "'JetBrains Mono', monospace",
                        size: 10
                    }
                }
            },
            y: {
                grid: {
                    color: 'rgba(255, 255, 255, 0.05)'
                },
                ticks: {
                    color: '#94a3b8', // --text-muted
                    font: {
                        family: "'JetBrains Mono', monospace",
                        size: 10
                    },
                    callback: (value) => '$' + value.toFixed(4)
                }
            }
        },
        interaction: {
            mode: 'nearest',
            axis: 'x',
            intersect: false
        }
    };

    return (
        <div className="trading-graph-container">
            <Line data={chartData} options={options} />
        </div>
    );
};

export default TradingGraph;
