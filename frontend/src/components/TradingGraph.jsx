import React, { useMemo, useEffect, useState } from 'react';
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
    const [screenSize, setScreenSize] = useState({
        width: window.innerWidth,
        isMobile: window.innerWidth < 768,
        isTablet: window.innerWidth >= 768 && window.innerWidth < 1024,
        isDesktop: window.innerWidth >= 1024
    });

    useEffect(() => {
        const handleResize = () => {
            const width = window.innerWidth;
            setScreenSize({
                width,
                isMobile: width < 768,
                isTablet: width >= 768 && width < 1024,
                isDesktop: width >= 1024
            });
        };

        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

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
            markerType: null,
        };

        // 2. Transaction points
        const points = transactionHistory.map((tx, idx) => {
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

        // Responsive point sizes
        const pointRadius = screenSize.isMobile ? 5 : 6;
        const pointHoverRadius = screenSize.isMobile ? 7 : 8;

        return {
            labels: dataPoints.map(p => p.x),
            datasets: [
                {
                    label: 'Price Action',
                    data: dataPoints,
                    borderColor: '#bef264',
                    backgroundColor: (context) => {
                        const ctx = context.chart.ctx;
                        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
                        gradient.addColorStop(0, 'rgba(190, 242, 100, 0.5)');
                        gradient.addColorStop(1, 'rgba(190, 242, 100, 0.0)');
                        return gradient;
                    },
                    borderWidth: screenSize.isMobile ? 1.5 : 2,
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: (context) => {
                        const index = context.dataIndex;
                        const point = context.dataset.data[index];
                        if (point.action === 'buy') return '#10b981';
                        if (point.action === 'sell') return '#ef4444';
                        return '#475569';
                    },
                    pointBorderColor: '#fff',
                    pointBorderWidth: screenSize.isMobile ? 1.5 : 2,
                    pointRadius: pointRadius,
                    pointHoverRadius: pointHoverRadius,
                },
            ],
        };
    }, [transactionHistory, basePrice, screenSize]);

    const options = useMemo(() => ({
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: false,
            },
            tooltip: {
                backgroundColor: 'rgba(15, 23, 42, 0.9)',
                titleColor: '#f8fafc',
                bodyColor: '#cbd5e1',
                borderColor: 'rgba(255, 255, 255, 0.1)',
                borderWidth: 1,
                padding: screenSize.isMobile ? 8 : 12,
                displayColors: false,
                bodyFont: {
                    size: screenSize.isMobile ? 11 : 12
                },
                titleFont: {
                    size: screenSize.isMobile ? 12 : 13,
                    weight: 'bold'
                },
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
                    color: '#94a3b8',
                    maxTicksLimit: screenSize.isMobile ? 4 : screenSize.isTablet ? 5 : 6,
                    font: {
                        family: "'JetBrains Mono', monospace",
                        size: screenSize.isMobile ? 8 : 10
                    },
                    maxRotation: screenSize.isMobile ? 45 : 0,
                    minRotation: screenSize.isMobile ? 45 : 0
                }
            },
            y: {
                grid: {
                    color: 'rgba(255, 255, 255, 0.05)'
                },
                ticks: {
                    color: '#94a3b8',
                    font: {
                        family: "'JetBrains Mono', monospace",
                        size: screenSize.isMobile ? 8 : 10
                    },
                    callback: (value) => screenSize.isMobile ? `$${value.toFixed(2)}` : `$${value.toFixed(4)}`
                }
            }
        },
        interaction: {
            mode: 'nearest',
            axis: 'x',
            intersect: false
        }
    }), [screenSize]);

    return (
        <div 
            className="trading-graph-container" 
            style={{
                height: screenSize.isMobile ? '300px' : screenSize.isTablet ? '350px' : '400px',
                width: '100%',
                padding: screenSize.isMobile ? '10px' : '15px'
            }}
        >
            <Line data={chartData} options={options} />
        </div>
    );
};

export default TradingGraph;