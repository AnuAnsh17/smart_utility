'use client';

import React, { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { AppStage, AnalysisResult } from '@/types/analysis';
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
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [showBillModal, setShowBillModal] = useState(false);

  // File Upload Handlers
  const handleFileSelect = (file: UploadedBillFile) => {
    setSelectedFile(file);
  };

  const handleUseSample = () => {
    const sampleFile: UploadedBillFile = {
      id: 'sample-oct-2024',
      name: 'electricity_bill_october.pdf',
      size: 1.2 * 1024 * 1024,
      type: 'application/pdf',
      isSample: true,
    };
    setSelectedFile(sampleFile);
    setIsDemoMode(false);
    setStage('processing');
  };

  const handleStartAnalysis = () => {
    setIsDemoMode(false);
    setStage('processing');
  };

  const handleProcessingComplete = () => {
    setStage('complete');
  };

  const handleExploreSampleDashboard = async () => {
    setIsDemoMode(true);
    const demoData = await analysisService.getSampleAnalysis();
    setAnalysisResult(demoData);
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
    setStage('landing');
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

        {/* STAGE 2: PROCESSING SCREEN (Real Upload / Sample Bill) */}
        {stage === 'processing' && (
          <motion.div key="processing-stage">
            <ProcessingScreen onComplete={handleProcessingComplete} />
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
                    onDownloadReport={() => alert('Downloading official PDF analysis report...')}
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
                    />
                  </div>
                </div>
              )}

              {/* TAB 3: FORECAST */}
              {activeTab === 'forecast' && (
                <ForecastView forecast={analysisResult.forecast} />
              )}

              {/* TAB 4: SAVINGS */}
              {activeTab === 'savings' && (
                <SavingsPage recommendations={analysisResult.recommendations} />
              )}

              {/* TAB 5: ASK ASSISTANT */}
              {activeTab === 'assistant' && <AssistantPanel />}

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
