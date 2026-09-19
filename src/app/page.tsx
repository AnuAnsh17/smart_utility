'use client';

import React, { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { AlertCircle, RotateCcw } from 'lucide-react';
import { AppStage, AnalysisResult, AnalysisMeta, LiveAnalysis } from '@/types/analysis';
import { UploadedBillFile } from '@/types/bill';
import { DashboardTab } from '@/components/layout/Sidebar';
import { LandingPage } from '@/components/upload/LandingPage';
import { ProcessingScreen } from '@/components/processing/ProcessingScreen';
import { PreparingSampleScreen } from '@/components/processing/PreparingSampleScreen';
import { AnalysisComplete } from '@/components/processing/AnalysisComplete';
import { DashboardShell } from '@/components/layout/DashboardShell';
import { DashboardHeader } from '@/components/dashboard/DashboardHeader';
import { TopMetricCards } from '@/components/dashboard/TopMetricCards';
import { MonthlyConsumptionChart } from '@/components/charts/MonthlyConsumptionChart';
import { ConsumptionBreakdownChart } from '@/components/charts/ConsumptionBreakdownChart';
import { AIInsightsCard } from '@/components/insights/AIInsightsCard';
import { WeatherImpactCard } from '@/components/weather/WeatherImpactCard';
import { TopRecommendationsCard } from '@/components/insights/TopRecommendationsCard';
import { QuickActionsCard } from '@/components/dashboard/QuickActionsCard';
import { ForecastView } from '@/components/forecast/ForecastView';
import { SavingsPage } from '@/components/insights/SavingsPage';
import { AssistantPanel } from '@/components/assistant/AssistantPanel';
import { DocumentsView } from '@/components/documents/DocumentsView';
import { BillDetailsModal } from '@/components/documents/BillDetailsModal';
import { analysisService, MOCK_ANALYSIS_RESULT } from '@/services/analysisService';

export default function Home() {
  const [stage, setStage] = useState<AppStage>('landing');
  const [activeTab, setActiveTab] = useState<DashboardTab>('dashboard');
  const [selectedFile, setSelectedFile] = useState<UploadedBillFile | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult>(MOCK_ANALYSIS_RESULT);
  const [analysisMeta, setAnalysisMeta] = useState<AnalysisMeta | null>(null);
  const [failureMessage, setFailureMessage] = useState<string | null>(null);
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [showBillModal, setShowBillModal] = useState(false);

  // File Upload Handlers
  const handleFileSelect = (file: UploadedBillFile) => {
    setSelectedFile(file);
  };

  // "Use a Sample Bill" is a demo affordance, and it now says so. It used to
  // fabricate a file record and push it through the real processing screen,
  // which meant a fabricated upload could masquerade as a genuine analysis.
  const handleUseSample = () => {
    void handleExploreSampleDashboard();
  };

  const handleStartAnalysis = () => {
    if (!selectedFile?.rawFile) return;
    setIsDemoMode(false);
    setFailureMessage(null);
    setStage('processing');
  };

  const handleProcessingComplete = (live: LiveAnalysis) => {
    setAnalysisResult(live.result);
    setAnalysisMeta(live.meta);
    setStage('complete');
  };

  const handleProcessingFailed = (message: string) => {
    setFailureMessage(message);
    setStage('failed');
  };

  const handleExploreSampleDashboard = async () => {
    setIsDemoMode(true);
    setFailureMessage(null);
    const demoData = await analysisService.getSampleAnalysis();
    setAnalysisResult(demoData);
    setAnalysisMeta(null);
    setStage('preparing_demo');
  };

  const handleSamplePrepComplete = () => {
    setStage('dashboard');
    setActiveTab('dashboard');
  };

  const handleOpenDashboard = () => {
    setStage('dashboard');
    setActiveTab('dashboard');
  };

  const handleExitDemo = () => {
    setIsDemoMode(false);
    setSelectedFile(null);
    setAnalysisMeta(null);
    setFailureMessage(null);
    setStage('landing');
  };

  // Exports the analysis the screen is already showing. It is built from the
  // live result and job metadata rather than a canned document, so the file
  // contains exactly the numbers on screen and nothing invented.
  const handleDownloadReport = () => {
    const payload = {
      job_id: analysisMeta?.jobId ?? null,
      generated_from: isDemoMode ? 'sample-data' : 'uploaded-bill',
      bill: analysisResult.bill,
      forecast: analysisResult.forecast,
      weather: analysisResult.weather,
      insights: analysisResult.insights,
      recommendations: analysisResult.recommendations,
      validation: analysisMeta
        ? {
            warnings: analysisMeta.warnings,
            missing_fields: analysisMeta.missingFields,
            detected_language: analysisMeta.detectedLanguage,
            ocr_engine: analysisMeta.ocrEngine,
            ocr_mean_confidence: analysisMeta.ocrMeanConfidence,
            timings: analysisMeta.timings,
          }
        : null,
    };

    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `bill-analysis-${analysisMeta?.jobId ?? 'sample'}.json`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  };

  const handleQuickAction = (key: string) => {
    if (key === 'details') {
      setShowBillModal(true);
    } else if (key === 'forecast3m') {
      setActiveTab('forecast');
    } else if (key === 'savingsTips') {
      setActiveTab('savings');
    } else if (key === 'compare') {
      setActiveTab('consumption');
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 font-sans selection:bg-emerald-500/20">
      <AnimatePresence mode="wait">
        {/* STAGE 1: LANDING PAGE */}
        {stage === 'landing' && (
          <motion.div key="landing-stage">
            <LandingPage
              onFileSelect={handleFileSelect}
              onUseSample={handleUseSample}
              onStartAnalysis={handleStartAnalysis}
              selectedFile={selectedFile}
              onClearFile={() => setSelectedFile(null)}
              isDemoMode={isDemoMode}
              onToggleDemoMode={setIsDemoMode}
              onExploreSampleDashboard={handleExploreSampleDashboard}
            />
          </motion.div>
        )}

        {/* STAGE 2: PROCESSING SCREEN — real upload against the local backend */}
        {stage === 'processing' && selectedFile?.rawFile && (
          <motion.div key="processing-stage">
            <ProcessingScreen
              key={selectedFile.id}
              file={selectedFile.rawFile}
              onComplete={handleProcessingComplete}
              onFailed={handleProcessingFailed}
            />
          </motion.div>
        )}

        {/* STAGE 2b: ANALYSIS FAILED */}
        {stage === 'failed' && (
          <motion.div
            key="failed-stage"
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            className="min-h-screen bg-slate-50/60 flex items-center justify-center p-6 font-sans"
          >
            <div className="w-full max-w-md bg-white border border-slate-200/80 rounded-2xl p-7 shadow-md text-center">
              <div className="w-12 h-12 rounded-2xl bg-rose-50 text-rose-600 border border-rose-100 flex items-center justify-center mx-auto mb-4">
                <AlertCircle className="w-6 h-6 stroke-[2]" />
              </div>
              <h2 className="text-lg font-extrabold text-slate-900 mb-2">
                We could not analyse this bill
              </h2>
              <p className="text-sm text-slate-500 leading-relaxed mb-6">
                {failureMessage}
              </p>
              <div className="flex items-center justify-center gap-3">
                <button
                  type="button"
                  onClick={handleExitDemo}
                  className="px-5 py-2.5 rounded-full border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-bold transition-colors inline-flex items-center gap-2 cursor-pointer"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  Try another bill
                </button>
              </div>
            </div>
          </motion.div>
        )}

        {/* STAGE 3: DEMO PREPARATION TRANSITION */}
        {stage === 'preparing_demo' && (
          <motion.div key="demo-prep-stage">
            <PreparingSampleScreen onComplete={handleSamplePrepComplete} />
          </motion.div>
        )}

        {/* STAGE 4: ANALYSIS COMPLETE */}
        {stage === 'complete' && (
          <motion.div key="complete-stage">
            <AnalysisComplete
              bill={analysisResult.bill}
              meta={analysisMeta}
              onOpenDashboard={handleOpenDashboard}
            />
          </motion.div>
        )}

        {/* STAGE 5: MAIN ANALYTICS DASHBOARD (Used by both Real & Demo Mode) */}
        {stage === 'dashboard' && (
          <motion.div
            key="dashboard-stage"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4 }}
          >
            <DashboardShell
              activeTab={activeTab}
              onSelectTab={(tab) => {
                if (tab === 'analyze') {
                  handleExitDemo();
                } else {
                  setActiveTab(tab);
                }
              }}
              location={analysisResult.weather.location}
              tempC={analysisResult.weather.tempC}
              isDemoMode={isDemoMode}
              onExitDemo={handleExitDemo}
            >
              {/* TAB 1: DASHBOARD OVERVIEW */}
              {activeTab === 'dashboard' && (
                <div className="space-y-6">
                  <DashboardHeader
                    onDownloadReport={handleDownloadReport}
                    onAskAssistant={() => setActiveTab('assistant')}
                  />

                  {/* Top Metric Cards */}
                  <TopMetricCards
                    bill={analysisResult.bill}
                    forecast={analysisResult.forecast}
                  />

                  {/* Middle Grid: Charts & AI Insights */}
                  <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                    <div className="lg:col-span-5">
                      <MonthlyConsumptionChart
                        data={analysisResult.forecast.historicalTrend}
                        currencySymbol={analysisResult.bill.currencySymbol}
                      />
                    </div>
                    <div className="lg:col-span-4">
                      <ConsumptionBreakdownChart
                        data={analysisResult.forecast.applianceBreakdown}
                        totalKwh={analysisResult.bill.unitsConsumed}
                      />
                    </div>
                    <div className="lg:col-span-3">
                      <AIInsightsCard
                        insights={analysisResult.insights}
                        onViewAll={() => setActiveTab('savings')}
                      />
                    </div>
                  </div>

                  {/* Bottom Grid: Weather, Recommendations & Quick Actions */}
                  <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                    <div className="lg:col-span-4">
                      <WeatherImpactCard weather={analysisResult.weather} />
                    </div>
                    <div className="lg:col-span-4">
                      <TopRecommendationsCard
                        recommendations={analysisResult.recommendations}
                        onViewAll={() => setActiveTab('savings')}
                      />
                    </div>
                    <div className="lg:col-span-4">
                      <QuickActionsCard onAction={handleQuickAction} />
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 2: CONSUMPTION ANALYTICS */}
              {activeTab === 'consumption' && (
                <div className="space-y-6">
                  <div className="p-6 bg-white rounded-2xl border border-slate-200/80 shadow-xs">
                    <h2 className="text-xl font-extrabold text-slate-900 mb-1">
                      Consumption History & Trend Analysis
                    </h2>
                    <p className="text-xs text-slate-500 mb-6">
                      Historical unit breakdown and month-on-month variance.
                    </p>
                    <MonthlyConsumptionChart
                      data={analysisResult.forecast.historicalTrend}
                      currencySymbol={analysisResult.bill.currencySymbol}
                    />
                  </div>
                </div>
              )}

              {/* TAB 3: FORECAST */}
              {activeTab === 'forecast' && (
                <ForecastView
                  forecast={analysisResult.forecast}
                  currencySymbol={analysisResult.bill.currencySymbol}
                />
              )}

              {/* TAB 4: SAVINGS */}
              {activeTab === 'savings' && (
                <SavingsPage recommendations={analysisResult.recommendations} />
              )}

              {/* TAB 5: ASK ASSISTANT */}
              {activeTab === 'assistant' && (
                <AssistantPanel
                  jobId={analysisMeta?.jobId ?? null}
                  billLabel={
                    analysisResult.bill.provider && analysisResult.bill.billingPeriod
                      ? `${analysisResult.bill.provider}, ${analysisResult.bill.billingPeriod}`
                      : analysisResult.bill.billingPeriod
                  }
                />
              )}

              {/* TAB 6: DOCUMENTS */}
              {activeTab === 'documents' && (
                <DocumentsView
                  onViewBillDetails={() => setShowBillModal(true)}
                  onUploadNewBill={handleExitDemo}
                />
              )}
            </DashboardShell>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Bill Details Modal */}
      {showBillModal && (
        <BillDetailsModal
          bill={analysisResult.bill}
          onClose={() => setShowBillModal(false)}
        />
      )}
    </div>
  );
}
