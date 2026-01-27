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
                    borderColor: '#3b82f6', // Primary Blue
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    tension: 0.1, // Slight curve, but mostly straight lines as requested "joint with line"
                    fill: true,
                    pointBackgroundColor: (context) => {
                        const index = context.dataIndex;
                        const point = context.dataset.data[index];
                        if (point.action === 'buy') return '#22c55e'; // Green
                        if (point.action === 'sell') return '#ef4444'; // Red
                        return '#6b7280'; // Gray for start
                    },
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 8, // Large enough for text
                    pointHoverRadius: 10,
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
                backgroundColor: 'rgba(0, 0, 0, 0.9)',
                titleColor: '#fff',
                bodyColor: '#ccc',
                borderColor: '#333',
                borderWidth: 1,
                padding: 10,
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
                    color: 'rgba(255, 255, 255, 0.1)'
                },
                ticks: {
                    color: '#888',
                    maxTicksLimit: 8
                }
            },
            y: {
                grid: {
                    color: 'rgba(255, 255, 255, 0.05)'
                },
                ticks: {
                    color: '#888',
                    callback: (value) => '$' + value.toFixed(4)
                }
            }
        },
        interaction: {
            mode: 'nearest',
            axis: 'x',
            intersect: true
        }
    };

    return (
        <div style={{ height: '350px', width: '100%' }}>
            <Line data={chartData} options={options} />
        </div>
    );
};

export default TradingGraph;
